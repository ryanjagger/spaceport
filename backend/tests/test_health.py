from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import normalise_database_url
from app.db import get_session
from app.main import app


def test_health_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_503_when_database_unreachable():
    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )

    def override_session() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get("/api/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503


def test_database_url_scheme_is_rewritten_for_psycopg():
    assert normalise_database_url("postgresql://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalise_database_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalise_database_url("postgresql+psycopg://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
