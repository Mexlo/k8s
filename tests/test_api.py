"""E2E-тести REST API (запускаються на сховищі в пам'яті, а за наявності
змінної TEST_DATABASE_URL ще й на реальному PostgreSQL)."""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from lab4.api import create_app
from lab4.db_init import init_db
from lab4.repository import GroupRepository, InMemoryGroupRepository, PostgresGroupRepository

VALID = {
    "name": "RedHack",
    "founded": 1997,
    "ideology": "Інше",
    "active": True,
    "last_action": "2012-03-15",
}


def _repos() -> list[str]:
    names = ["memory"]
    if os.environ.get("TEST_DATABASE_URL"):
        names.append("postgres")
    return names


@pytest.fixture(params=_repos())
def client(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    repo: GroupRepository
    if request.param == "memory":
        repo = InMemoryGroupRepository()
    else:
        dsn = os.environ["TEST_DATABASE_URL"]
        init_db(dsn)
        repo = PostgresGroupRepository(dsn)
    with TestClient(create_app(repo)) as c:
        yield c


def test_full_crud_cycle(client: TestClient) -> None:
    created = client.post("/api/groups", json=VALID)
    assert created.status_code == 201
    body = created.json()
    gid = body["id"]
    assert body["name"] == "RedHack"
    assert body["last_action"] == "2012-03-15"

    assert client.get(f"/api/groups/{gid}").status_code == 200
    assert any(g["id"] == gid for g in client.get("/api/groups").json())

    changed = client.put(f"/api/groups/{gid}", json={**VALID, "name": "RedHack 2"})
    assert changed.status_code == 200
    assert changed.json()["name"] == "RedHack 2"

    assert client.delete(f"/api/groups/{gid}").status_code == 200
    assert client.get(f"/api/groups/{gid}").status_code == 404
    assert client.delete(f"/api/groups/{gid}").status_code == 404


@pytest.mark.parametrize(
    "patch",
    [
        {"name": ""},
        {"name": "<script>"},
        {"founded": 1900},
        {"last_action": "15.03.2012"},
    ],
)
def test_validation_rejects_bad_input(client: TestClient, patch: dict[str, object]) -> None:
    response = client.post("/api/groups", json={**VALID, **patch})
    assert response.status_code == 400
    assert "error" in response.json()


def test_missing_record_returns_404(client: TestClient) -> None:
    response = client.get("/api/groups/999999")
    assert response.status_code == 404
    assert response.json() == {"error": "Запис не знайдено"}


def test_actions_of_group(client: TestClient) -> None:
    gid = client.post("/api/groups", json=VALID).json()["id"]
    actions = client.get(f"/api/groups/{gid}/actions")
    assert actions.status_code == 200
    assert len(actions.json()) == 1
    assert client.get("/api/groups/999999/actions").status_code == 404
    client.delete(f"/api/groups/{gid}")


def test_ideology_with_slash_is_allowed(client: TestClient) -> None:
    payload = {**VALID, "name": "SlashTest", "ideology": "Політична / державна"}
    response = client.post("/api/groups", json=payload)
    assert response.status_code == 201
    client.delete(f"/api/groups/{response.json()['id']}")
