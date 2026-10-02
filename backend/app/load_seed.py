"""Load the seed file into an empty database. Safe to run on every start.

    python -m app.load_seed

Does nothing if the bookings table already has rows. The whole load is one
transaction: any invalid or conflicting row fails it and commits nothing.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, text

from app import rules
from app.config import get_settings
from app.db import get_engine

log = logging.getLogger("spaceport.load_seed")

# Arbitrary key; stops two instances that start together from both loading.
SEED_LOCK_KEY = 7002


class SeedError(ValueError):
    pass


def _parse_booking(index: int, raw: dict, ship_ids: set[int]) -> dict:
    """Check one seed row against the rules the database cannot enforce.

    The exclusion constraint covers overlap and buffer; hours, grid and duration
    are checked here. History is exempt from the no-past-bookings rule.
    """
    try:
        start = datetime.fromisoformat(raw["startTime"])
        end = datetime.fromisoformat(raw["endTime"])
        pilot = raw["pilotName"].strip()
        if raw["shipId"] not in ship_ids:
            raise ValueError(f"unknown ship {raw['shipId']}")
        if not 1 <= len(pilot) <= 100:
            raise ValueError("pilot name must be 1-100 characters")
        rules.check_interval(start, end)
    except (KeyError, AttributeError, TypeError, ValueError, rules.RuleViolation) as exc:
        raise SeedError(f"seed booking #{index} is invalid ({exc!r}): {raw}") from exc
    return {"ship_id": raw["shipId"], "pilot_name": pilot, "start_time": start, "end_time": end}


def load_seed(engine: Engine, path: Path) -> int:
    """Insert the ships and bookings in `path`. Returns the number of bookings inserted."""
    data = json.loads(path.read_text())

    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK_KEY})
        if conn.execute(text("SELECT EXISTS (SELECT 1 FROM bookings)")).scalar_one():
            return 0

        ships = [{"id": s["id"], "name": s["name"]} for s in data["ships"]]
        ship_ids = {s["id"] for s in ships}
        bookings = [_parse_booking(i, raw, ship_ids) for i, raw in enumerate(data["bookings"])]

        if ships:
            conn.execute(
                text(
                    "INSERT INTO ships (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"
                ),
                ships,
            )
        if bookings:
            conn.execute(
                text(
                    "INSERT INTO bookings (ship_id, pilot_name, start_time, end_time) "
                    "VALUES (:ship_id, :pilot_name, :start_time, :end_time)"
                ),
                bookings,
            )
        return len(bookings)


def main() -> None:
    # stdout, not the default stderr: Railway labels anything on stderr as an error.
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stdout)
    path = get_settings().seed_file
    inserted = load_seed(get_engine(), path)
    if inserted:
        log.info("loaded %d bookings from %s", inserted, path)
    else:
        log.info("bookings already present (or seed empty); nothing loaded")


if __name__ == "__main__":
    main()
