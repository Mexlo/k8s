"""Доменні класи: сутності предметної області «Хактивістські угруповання»."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Ideology:
    """Ідеологія. Зв'язок із Group: N:1 (багато груп мають одну ідеологію)."""

    id: int
    name: str


@dataclass(frozen=True)
class Target:
    """Ціль/сектор атак. Зв'язок із Group: N:M."""

    id: int
    name: str


@dataclass(frozen=True)
class Action:
    """Акція угруповання. Зв'язок із Group: N:1 (в групи багато акцій, тобто 1:N)."""

    id: int
    group_id: int
    title: str
    date: date


@dataclass
class Group:
    """Хактивістське угруповання."""

    id: int
    name: str
    founded: int
    ideology: str
    active: bool
    last_action: date | None = None
    targets: list[str] = field(default_factory=list)
