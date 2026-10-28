"""Ініціалізація бази: SQL-скрипт створення таблиць і вставки тестових даних.

Запуск: ``uv run python -m lab4.db_init``
"""

import os

import psycopg

from lab4.seed import GROUPS, IDEOLOGIES, TARGETS

DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ideologies (
    id   serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS targets (
    id   serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS groups (
    id          serial PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    founded     integer NOT NULL CHECK (founded BETWEEN 1970 AND 2026),
    ideology_id integer NOT NULL REFERENCES ideologies(id),
    active      boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS actions (
    id       serial PRIMARY KEY,
    group_id integer NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    title    text NOT NULL,
    date     date NOT NULL
);
CREATE TABLE IF NOT EXISTS group_targets (
    group_id  integer NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    target_id integer NOT NULL REFERENCES targets(id),
    PRIMARY KEY (group_id, target_id)
);
"""


def init_db(dsn: str) -> None:
    """Створює таблиці й, якщо база порожня, вставляє тестові дані."""
    with psycopg.connect(dsn) as conn:
        conn.execute(SCHEMA)
        count = conn.execute("SELECT count(*) FROM groups").fetchone()
        if count and count[0] > 0:
            return

        for name in IDEOLOGIES:
            conn.execute("INSERT INTO ideologies (name) VALUES (%s)", (name,))
        for name in TARGETS:
            conn.execute("INSERT INTO targets (name) VALUES (%s)", (name,))

        for group in GROUPS:
            row = conn.execute(
                "INSERT INTO groups (name, founded, ideology_id, active) "
                "VALUES (%s, %s, (SELECT id FROM ideologies WHERE name = %s), %s) RETURNING id",
                (group.name, group.founded, group.ideology, group.active),
            ).fetchone()
            assert row is not None
            group_id = row[0]

            title, date = group.known_action
            conn.execute(
                "INSERT INTO actions (group_id, title, date) VALUES (%s, %s, %s)",
                (group_id, title, date),
            )
            for k in range(1, 3):  # демонстраційні акції для обсягу даних
                conn.execute(
                    "INSERT INTO actions (group_id, title, date) VALUES (%s, %s, %s)",
                    (group_id, f"Демонстраційна акція №{k}", f"{group.founded}-01-0{k}"),
                )
            for target in group.targets:
                conn.execute(
                    "INSERT INTO group_targets (group_id, target_id) "
                    "VALUES (%s, (SELECT id FROM targets WHERE name = %s))",
                    (group_id, target),
                )


if __name__ == "__main__":
    init_db(os.environ.get("DATABASE_URL", DEFAULT_DSN))
    print("База ініціалізована")
