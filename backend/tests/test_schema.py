"""The database's own rules, tested with direct SQL: no API, no service layer."""

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.init_db import (
    CONSTRAINT_NAME,
    SchemaMismatchError,
    apply_schema,
    drop_tables,
    init_db,
    verify_constraint,
)
from app.models import Base
from tests.conftest import check_test_database

EXCLUSION_VIOLATION = "23P01"
CHECK_VIOLATION = "23514"

# Postgres must give the same answer whatever the session timezone is.
SESSION_TIMEZONES = ["UTC", "Asia/Tokyo"]


def insert(engine: Engine, start: str, end: str, *, ship_id=1, status="active", pilot="Pilot",
           tz="UTC") -> None:  # fmt: skip
    """Insert one booking in its own transaction. Times are 2026-10-02, Central (-05:00)."""
    with engine.begin() as conn:
        conn.execute(text(f"SET LOCAL TIME ZONE '{tz}'"))
        conn.execute(
            text(
                "INSERT INTO bookings (ship_id, pilot_name, start_time, end_time, status) "
                "VALUES (:ship_id, :pilot, :start, :end, :status)"
            ),
            {
                "ship_id": ship_id,
                "pilot": pilot,
                "start": f"2026-10-02T{start}:00-05:00",
                "end": f"2026-10-02T{end}:00-05:00",
                "status": status,
            },
        )


def assert_rejected(sqlstate: str, engine: Engine, *args, **kwargs) -> None:
    with pytest.raises(IntegrityError) as exc:
        insert(engine, *args, **kwargs)
    assert exc.value.orig.sqlstate == sqlstate


def test_exclusion_constraint_exists(db: Engine):
    with db.connect() as conn:
        contype = conn.execute(
            text(
                "SELECT contype FROM pg_constraint "
                "WHERE conrelid = 'bookings'::regclass AND conname = :name"
            ),
            {"name": CONSTRAINT_NAME},
        ).scalar_one()
    assert contype == "x"  # exclusion constraint


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_overlap_rejected(db: Engine, tz: str):
    insert(db, "08:00", "10:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "09:00", "11:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "07:00", "08:30", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "08:30", "09:00", tz=tz)


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_touching_bookings_rejected(db: Engine, tz: str):
    insert(db, "08:00", "10:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "10:00", "11:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "07:00", "08:00", tz=tz)


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_29_minute_gap_rejected(db: Engine, tz: str):
    insert(db, "08:00", "10:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "10:29", "11:00", tz=tz)  # after
    assert_rejected(EXCLUSION_VIOLATION, db, "07:00", "07:31", tz=tz)  # before


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_exactly_30_minute_gap_accepted(db: Engine, tz: str):
    insert(db, "08:00", "10:00", tz=tz)
    insert(db, "10:30", "11:00", tz=tz)  # after
    insert(db, "07:00", "07:30", tz=tz)  # before


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_other_ships_never_conflict(db: Engine, tz: str):
    insert(db, "08:00", "10:00", ship_id=1, tz=tz)
    insert(db, "08:00", "10:00", ship_id=2, tz=tz)


@pytest.mark.parametrize("tz", SESSION_TIMEZONES)
def test_cancelled_rows_never_conflict(db: Engine, tz: str):
    insert(db, "08:00", "10:00", status="cancelled", tz=tz)
    insert(db, "08:00", "10:00", status="cancelled", tz=tz)
    insert(db, "08:00", "10:00", tz=tz)
    assert_rejected(EXCLUSION_VIOLATION, db, "08:00", "10:00", tz=tz)


def test_end_must_be_after_start(db: Engine):
    assert_rejected(CHECK_VIOLATION, db, "08:00", "08:00")
    assert_rejected(CHECK_VIOLATION, db, "09:00", "08:00")


def test_unknown_status_rejected(db: Engine):
    assert_rejected(CHECK_VIOLATION, db, "08:00", "09:00", status="pending")


def test_pilot_name_length(db: Engine):
    insert(db, "06:00", "07:00", pilot="x" * 100)
    insert(db, "08:00", "09:00", pilot="  " + "x" * 100 + "  ")  # 100 after trimming
    assert_rejected(CHECK_VIOLATION, db, "10:00", "11:00", pilot="x" * 101)
    assert_rejected(CHECK_VIOLATION, db, "10:00", "11:00", pilot="   ")


def test_models_match_database(db: Engine):
    inspector = inspect(db)
    for table in Base.metadata.sorted_tables:
        actual = {c["name"]: c for c in inspector.get_columns(table.name)}
        assert set(actual) == {c.name for c in table.columns}, table.name
        for column in table.columns:
            reflected = actual[column.name]
            where = f"{table.name}.{column.name}"
            assert isinstance(reflected["type"], type(column.type)), where
            assert reflected["nullable"] == column.nullable, where
            assert getattr(reflected["type"], "timezone", None) == getattr(
                column.type, "timezone", None
            ), where


def test_applying_schema_twice_changes_nothing(db: Engine):
    insert(db, "08:00", "10:00")
    apply_schema(db)
    verify_constraint(db)
    with db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM bookings")).scalar_one() == 1


class TestStartupGuard:
    @pytest.fixture(autouse=True)
    def restore_schema(self, engine: Engine):
        yield
        init_db(engine, reset=True)

    def test_refuses_when_constraint_missing(self, engine: Engine):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE bookings DROP CONSTRAINT {CONSTRAINT_NAME}"))
        with pytest.raises(SchemaMismatchError, match="missing"):
            init_db(engine)

    def test_refuses_when_constraint_differs(self, engine: Engine):
        # An older table with a 29-minute buffer: schema.sql skips it (IF NOT EXISTS).
        drop_tables(engine)
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE ships (id integer PRIMARY KEY, name text)"))
            conn.execute(
                text(
                    "CREATE TABLE bookings (ship_id integer, start_time timestamptz, "
                    "end_time timestamptz, status text, "
                    f"CONSTRAINT {CONSTRAINT_NAME} EXCLUDE USING gist (ship_id WITH =, "
                    "tsrange(start_time AT TIME ZONE 'UTC', "
                    "(end_time AT TIME ZONE 'UTC') + interval '29 minutes', '[)') WITH &&) "
                    "WHERE (status = 'active'))"
                )
            )
        with pytest.raises(SchemaMismatchError, match="differs"):
            init_db(engine)


class TestDatabaseGuard:
    MAIN = "postgresql+psycopg://u:p@db/spaceport"

    def test_accepts_a_separate_test_database(self):
        url = "postgresql+psycopg://u:p@db/spaceport_test"
        assert check_test_database(url, self.MAIN) == url

    def test_refuses_missing_url(self):
        with pytest.raises(RuntimeError, match="not set"):
            check_test_database(None, self.MAIN)

    def test_refuses_name_without_test_suffix(self):
        with pytest.raises(RuntimeError, match="_test"):
            check_test_database(self.MAIN, "postgresql+psycopg://u:p@db/other")

    def test_refuses_same_database_as_app(self):
        url = "postgresql+psycopg://u:p@db/spaceport_test"
        with pytest.raises(RuntimeError, match="differ"):
            check_test_database(url, url)
