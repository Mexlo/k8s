"""Сховище даних.

Принцип відкритості/закритості (OCP): API залежить лише від протоколу
``GroupRepository``. Щоб додати нове сховище (MongoDB, Redis), достатньо
написати новий клас із цими методами; наявний код змінювати не потрібно.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from lab4.domain import Action, Group
from lab4.schemas import GroupIn


def _int(value: object) -> int:
    """Безпечне перетворення значення з бази на ціле число."""
    assert isinstance(value, int)
    return value


class GroupRepository(Protocol):
    """Контракт, який має виконувати будь-яке сховище."""

    def list_groups(self) -> list[Group]: ...

    def get_group(self, group_id: int) -> Group | None: ...

    def create_group(self, data: GroupIn) -> Group: ...

    def update_group(self, group_id: int, data: GroupIn) -> Group | None: ...

    def delete_group(self, group_id: int) -> bool: ...

    def list_actions(self, group_id: int) -> list[Action] | None: ...


class InMemoryGroupRepository:
    """Сховище в пам'яті процесу (для тестів і запуску без бази)."""

    def __init__(self) -> None:
        self._groups: dict[int, Group] = {}
        self._actions: dict[int, list[Action]] = {}
        self._next_group_id = 1
        self._next_action_id = 1

    def list_groups(self) -> list[Group]:
        return list(self._groups.values())

    def get_group(self, group_id: int) -> Group | None:
        return self._groups.get(group_id)

    def create_group(self, data: GroupIn) -> Group:
        group = Group(
            id=self._next_group_id,
            name=data.name,
            founded=data.founded,
            ideology=data.ideology,
            active=data.active,
        )
        self._groups[group.id] = group
        self._actions[group.id] = []
        self._next_group_id += 1
        if data.last_action:
            self._add_action(group, data.last_action)
        return group

    def _add_action(self, group: Group, raw_date: str) -> None:
        action = Action(
            id=self._next_action_id,
            group_id=group.id,
            title="Відома акція",
            date=date.fromisoformat(raw_date),
        )
        self._next_action_id += 1
        self._actions[group.id].append(action)
        group.last_action = max(a.date for a in self._actions[group.id])

    def update_group(self, group_id: int, data: GroupIn) -> Group | None:
        group = self._groups.get(group_id)
        if group is None:
            return None
        group.name = data.name
        group.founded = data.founded
        group.ideology = data.ideology
        group.active = data.active
        if data.last_action:
            self._add_action(group, data.last_action)
        return group

    def delete_group(self, group_id: int) -> bool:
        self._actions.pop(group_id, None)
        return self._groups.pop(group_id, None) is not None

    def list_actions(self, group_id: int) -> list[Action] | None:
        if group_id not in self._groups:
            return None
        return list(self._actions[group_id])


GROUP_SELECT = """
    SELECT g.id, g.name, g.founded, i.name AS ideology, g.active,
           (SELECT max(a.date) FROM actions a WHERE a.group_id = g.id) AS last_action,
           COALESCE(
               (SELECT array_agg(t.name ORDER BY t.name)
                  FROM group_targets gt JOIN targets t ON t.id = gt.target_id
                 WHERE gt.group_id = g.id),
               ARRAY[]::text[]
           ) AS targets
      FROM groups g
      JOIN ideologies i ON i.id = g.ideology_id
"""


class PostgresGroupRepository:
    """Сховище на PostgreSQL. Усі запити параметризовані (захист від SQL-ін'єкцій)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def _conn(self) -> Iterator[psycopg.Connection[dict[str, object]]]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            yield conn

    @staticmethod
    def _to_group(row: dict[str, object]) -> Group:
        return Group(
            id=int(row["id"]),  # type: ignore[call-overload]
            name=str(row["name"]),
            founded=int(row["founded"]),  # type: ignore[call-overload]
            ideology=str(row["ideology"]),
            active=bool(row["active"]),
            last_action=row["last_action"],  # type: ignore[arg-type]
            targets=list(row["targets"]),  # type: ignore[call-overload]
        )

    def list_groups(self) -> list[Group]:
        with self._conn() as conn:
            rows = conn.execute(GROUP_SELECT + " ORDER BY g.id").fetchall()
        return [self._to_group(r) for r in rows]

    def get_group(self, group_id: int) -> Group | None:
        with self._conn() as conn:
            row = conn.execute(GROUP_SELECT + " WHERE g.id = %s", (group_id,)).fetchone()
        return self._to_group(row) if row else None

    def _ideology_id(self, conn: psycopg.Connection[dict[str, object]], name: str) -> int:
        row = conn.execute(
            "INSERT INTO ideologies (name) VALUES (%s) "
            "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            (name,),
        ).fetchone()
        assert row is not None
        return _int(row["id"])

    def create_group(self, data: GroupIn) -> Group:
        with self._conn() as conn:
            ideology_id = self._ideology_id(conn, data.ideology)
            row = conn.execute(
                "INSERT INTO groups (name, founded, ideology_id, active) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (data.name, data.founded, ideology_id, data.active),
            ).fetchone()
            assert row is not None
            group_id = _int(row["id"])
            if data.last_action:
                conn.execute(
                    "INSERT INTO actions (group_id, title, date) VALUES (%s, %s, %s)",
                    (group_id, "Відома акція", data.last_action),
                )
        group = self.get_group(group_id)
        assert group is not None
        return group

    def update_group(self, group_id: int, data: GroupIn) -> Group | None:
        with self._conn() as conn:
            ideology_id = self._ideology_id(conn, data.ideology)
            cur = conn.execute(
                "UPDATE groups SET name = %s, founded = %s, ideology_id = %s, active = %s "
                "WHERE id = %s",
                (data.name, data.founded, ideology_id, data.active, group_id),
            )
            if cur.rowcount == 0:
                return None
            if data.last_action:
                conn.execute(
                    "INSERT INTO actions (group_id, title, date) VALUES (%s, %s, %s)",
                    (group_id, "Відома акція", data.last_action),
                )
        return self.get_group(group_id)

    def delete_group(self, group_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM groups WHERE id = %s", (group_id,))
            return cur.rowcount > 0

    def list_actions(self, group_id: int) -> list[Action] | None:
        with self._conn() as conn:
            exists = conn.execute("SELECT 1 FROM groups WHERE id = %s", (group_id,)).fetchone()
            if exists is None:
                return None
            rows = conn.execute(
                "SELECT id, group_id, title, date FROM actions WHERE group_id = %s ORDER BY date",
                (group_id,),
            ).fetchall()
        return [
            Action(
                id=int(r["id"]),  # type: ignore[call-overload]
                group_id=int(r["group_id"]),  # type: ignore[call-overload]
                title=str(r["title"]),
                date=r["date"],  # type: ignore[arg-type]
            )
            for r in rows
        ]
