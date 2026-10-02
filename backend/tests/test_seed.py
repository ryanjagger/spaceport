"""The seed loader, tested with small fixture files rather than data/seed.json."""

import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.load_seed import SeedError, load_seed

SHIPS = [{"id": 1, "name": "USS Wanderer"}, {"id": 2, "name": "Nostromo"}]


def booking(start: str, end: str, ship_id: int = 1, pilot: str = "Ellen Ripley") -> dict:
    """A seed row on 2025-11-03 (CST): history, like the real seed."""
    return {
        "shipId": ship_id,
        "pilotName": pilot,
        "startTime": f"2025-11-03T{start}:00-06:00",
        "endTime": f"2025-11-03T{end}:00-06:00",
    }


VALID = [
    booking("06:30", "08:30"),
    booking("09:30", "10:30"),  # 60 minutes after the previous one
    booking("06:30", "08:30", ship_id=2),
]


def write_seed(tmp_path: Path, bookings: list[dict], ships: list[dict] = SHIPS) -> Path:
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"ships": ships, "bookings": bookings}))
    return path


def counts(engine: Engine) -> tuple[int, int]:
    with engine.connect() as conn:
        ships = conn.execute(text("SELECT count(*) FROM ships")).scalar_one()
        bookings = conn.execute(text("SELECT count(*) FROM bookings")).scalar_one()
    return ships, bookings


def test_loads_ships_with_their_ids_and_all_bookings(empty_db: Engine, tmp_path: Path):
    assert load_seed(empty_db, write_seed(tmp_path, VALID)) == 3
    assert counts(empty_db) == (2, 3)
    with empty_db.connect() as conn:
        ships = conn.execute(text("SELECT id, name FROM ships ORDER BY id")).all()
        row = conn.execute(
            text("SELECT status, start_time AT TIME ZONE 'UTC' FROM bookings ORDER BY id LIMIT 1")
        ).one()
    assert [tuple(s) for s in ships] == [(1, "USS Wanderer"), (2, "Nostromo")]
    assert row[0] == "active"
    assert row[1].isoformat() == "2025-11-03T12:30:00"  # 6:30 AM CST, stored as an instant


def test_second_run_inserts_nothing(empty_db: Engine, tmp_path: Path):
    path = write_seed(tmp_path, VALID)
    load_seed(empty_db, path)
    assert load_seed(empty_db, path) == 0
    assert counts(empty_db) == (2, 3)


@pytest.mark.parametrize(
    "bad",
    [
        booking("05:30", "06:30"),  # before opening
        booking("21:00", "22:30"),  # after closing
        booking("09:15", "10:15"),  # off the grid
        booking("09:00", "18:00"),  # over 8 hours
        booking("09:00", "10:00", ship_id=9),  # unknown ship
        booking("09:00", "10:00", pilot="   "),  # blank name
        {**booking("09:00", "10:00"), "startTime": "2025-11-03T09:00:00"},  # no offset
        {"shipId": 1, "pilotName": "No Times"},
    ],
)
def test_invalid_row_fails_the_load_and_commits_nothing(empty_db: Engine, tmp_path, bad):
    with pytest.raises(SeedError, match="#3"):
        load_seed(empty_db, write_seed(tmp_path, [*VALID, bad]))
    assert counts(empty_db) == (0, 0)


def test_row_breaking_the_buffer_fails_on_the_database_constraint(empty_db: Engine, tmp_path):
    too_close = booking("08:30", "09:00")  # touches the first booking's end
    with pytest.raises(IntegrityError) as exc:
        load_seed(empty_db, write_seed(tmp_path, [*VALID, too_close]))
    assert exc.value.orig.sqlstate == "23P01"
    assert counts(empty_db) == (0, 0)


def test_failed_load_can_be_retried_in_full(empty_db: Engine, tmp_path: Path):
    with pytest.raises(SeedError):
        load_seed(empty_db, write_seed(tmp_path, [*VALID, booking("05:30", "06:30")]))
    assert load_seed(empty_db, write_seed(tmp_path, VALID)) == 3


def test_seed_with_no_bookings_still_loads_ships(empty_db: Engine, tmp_path: Path):
    assert load_seed(empty_db, write_seed(tmp_path, [])) == 0
    assert counts(empty_db) == (2, 0)
