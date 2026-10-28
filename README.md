# Лабораторна робота 4: Data Persistence & Web Interfaces

Каталог хактивістських угруповань: REST API на FastAPI + PostgreSQL у Docker.
Сторінку (HTML/CSS/JS з `fetch`) віддає той самий сервер, тому окремого CORS не потрібно.
Дані в базі навчальні й приблизні.

## Запуск

    docker compose up -d                 # PostgreSQL на порту 5432
    uv sync                              # залежності
    uv run uvicorn lab4.api:app --reload # сервер (база ініціалізується автоматично)

Сторінка: http://localhost:8000, документація API: http://localhost:8000/docs

Окремо ініціалізувати базу: `uv run python -m lab4.db_init`.
Без бази (сховище в пам'яті): змінна середовища `STORAGE=memory`.

## Перевірка якості

    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run pytest                                    # на сховищі в пам'яті
    TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres uv run pytest

## REST API

| Метод | Адреса | Дія | Коди |
|---|---|---|---|
| GET | /api/groups | список | 200 |
| GET | /api/groups/{id} | один запис | 200, 404 |
| POST | /api/groups | створити | 201, 400 |
| PUT | /api/groups/{id} | оновити | 200, 400, 404 |
| DELETE | /api/groups/{id} | видалити | 200, 404 |
| GET | /api/groups/{id}/actions | акції групи (1:N) | 200, 404 |

## Архітектура (принцип відкритості/закритості)

Маршрути в `api.py` залежать лише від протоколу `GroupRepository`
(`repository.py`). Реалізації: `PostgresGroupRepository`, `InMemoryGroupRepository`.
Щоб додати MongoDB чи Redis, потрібно написати новий клас із тими самими методами;
існуючий код не змінюється.

## Модель даних

Див. `docs/erd.md`.
