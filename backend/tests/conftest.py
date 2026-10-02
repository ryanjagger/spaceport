import os
from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import rules
from app.clock import get_now
from app.config import get_settings, normalise_database_url
from app.db import get_session
from app.init_db import init_db
from app.main import app


def check_test_database(test_url: str | None, main_url: str) -> str:
    """Tests drop and truncate tables, so refuse anything that isn't clearly a test database."""
    if not test_url:
        raise RuntimeError("TEST_DATABASE_URL is not set")
    name = make_url(test_url).database or ""
    if not name.endswith("_test"):
        raise RuntimeError(f"Refusing to run tests against {name!r}: name must end in _test")
    if make_url(test_url) == make_url(main_url):
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")
    return test_url


class FixedClock:
    """The injected "now". Defaults to the evening before the day most tests book on."""

    def __init__(self) -> None:
        self.now = datetime(2026, 10, 1, 21, 44, 12, tzinfo=rules.TZ)

    def set(self, central: str) -> None:
        """clock.set("2026-10-02 09:15") — Central wall-clock time."""
        self.now = datetime.fromisoformat(central).replace(tzinfo=rules.TZ)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_url = os.environ.get("TEST_DATABASE_URL")
    url = check_test_database(
        normalise_database_url(test_url) if test_url else None, get_settings().database_url
    )
    engine = create_engine(url)
    init_db(engine, reset=True)
    yield engine
    engine.dispose()


@pytest.fixture
def empty_db(engine: Engine) -> Engine:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE bookings, ships RESTART IDENTITY"))
    return engine


@pytest.fixture
def db(empty_db: Engine) -> Engine:
    """A test database with two ships and no bookings."""
    with empty_db.begin() as conn:
        conn.execute(text("INSERT INTO ships (id, name) VALUES (1, 'Serenity'), (2, 'Rocinante')"))
    return empty_db


@pytest.fixture
def api(db: Engine, clock: FixedClock) -> Iterator[None]:
    """Point the app at the test database and the fixed clock."""

    def override_session() -> Iterator[Session]:
        with Session(db) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_now] = lambda: clock.now
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(api: None) -> TestClient:
    return TestClient(app)
