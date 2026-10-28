"""REST API на FastAPI. Залежить лише від протоколу GroupRepository (OCP)."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from lab4.db_init import DEFAULT_DSN, init_db
from lab4.domain import Action, Group
from lab4.repository import (
    GroupRepository,
    InMemoryGroupRepository,
    PostgresGroupRepository,
)
from lab4.schemas import GroupIn
from lab4.seed import GROUPS

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


def build_repository() -> GroupRepository:
    """Вибір сховища зі змінної середовища STORAGE (postgres за замовчуванням)."""
    if os.environ.get("STORAGE", "postgres") == "memory":
        repo = InMemoryGroupRepository()
        for g in GROUPS:
            repo.create_group(
                GroupIn(
                    name=g.name,
                    founded=g.founded,
                    ideology=g.ideology,
                    active=g.active,
                    last_action=g.known_action[1],
                )
            )
        return repo
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    init_db(dsn)
    return PostgresGroupRepository(dsn)


def create_app(repo: GroupRepository | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if getattr(app.state, "repo", None) is None:
            app.state.repo = build_repository()
        yield

    app = FastAPI(title="Хактивістські групи", lifespan=lifespan)
    app.state.repo = repo

    def get_repo(request: Request) -> GroupRepository:
        repository: GroupRepository = request.app.state.repo
        return repository

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"] if p != "body")
        return JSONResponse(status_code=400, content={"error": f"Некоректне поле {field}"})

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/groups")
    def list_groups(repo: GroupRepository = Depends(get_repo)) -> list[Group]:
        return repo.list_groups()

    @app.get("/api/groups/{group_id}")
    def get_group(group_id: int, repo: GroupRepository = Depends(get_repo)) -> Group:
        group = repo.get_group(group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Запис не знайдено")
        return group

    @app.post("/api/groups", status_code=201)
    def create_group(data: GroupIn, repo: GroupRepository = Depends(get_repo)) -> Group:
        return repo.create_group(data)

    @app.put("/api/groups/{group_id}")
    def update_group(
        group_id: int, data: GroupIn, repo: GroupRepository = Depends(get_repo)
    ) -> Group:
        group = repo.update_group(group_id, data)
        if group is None:
            raise HTTPException(status_code=404, detail="Запис не знайдено")
        return group

    @app.delete("/api/groups/{group_id}")
    def delete_group(group_id: int, repo: GroupRepository = Depends(get_repo)) -> dict[str, bool]:
        if not repo.delete_group(group_id):
            raise HTTPException(status_code=404, detail="Запис не знайдено")
        return {"ok": True}

    @app.get("/api/groups/{group_id}/actions")
    def list_actions(group_id: int, repo: GroupRepository = Depends(get_repo)) -> list[Action]:
        actions = repo.list_actions(group_id)
        if actions is None:
            raise HTTPException(status_code=404, detail="Запис не знайдено")
        return actions

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
