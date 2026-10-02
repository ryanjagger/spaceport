"""Apply schema.sql and check the booking constraint is the one we expect.

python -m app.init_db            # safe to run on every start
python -m app.init_db --reset    # drop the tables first (destroys all bookings)
"""

import argparse
import logging
import sys
from datetime import timedelta

from sqlalchemy import Engine, text

from app import rules
from app.config import SCHEMA_FILE, get_settings
from app.db import get_engine

log = logging.getLogger("spaceport.init_db")

CONSTRAINT_NAME = "no_overlap_with_buffer"


def _pg_interval(delta: timedelta) -> str:
    """A sub-day interval the way Postgres prints it: 30 minutes is 00:30:00."""
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


# What pg_get_constraintdef returns for the constraint in schema.sql (Postgres 16).
# schema.sql is IF NOT EXISTS, so an edited constraint is silently skipped on an
# existing database; comparing the full definition catches that. The buffer comes
# from rules.py, so this also fails if schema.sql and the rules stop agreeing.
EXPECTED_CONSTRAINT_DEF = (
    "EXCLUDE USING gist (ship_id WITH =, "
    "tsrange((start_time AT TIME ZONE 'UTC'::text), "
    f"((end_time AT TIME ZONE 'UTC'::text) + '{_pg_interval(rules.REFUEL_BUFFER)}'::interval), "
    "'[)'::text) WITH &&) "
    "WHERE ((status = 'active'::text))"
)

# Arbitrary key; serialises schema setup when two instances start at once.
INIT_LOCK_KEY = 7001


class SchemaMismatchError(RuntimeError):
    pass


def apply_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": INIT_LOCK_KEY})
        conn.exec_driver_sql(SCHEMA_FILE.read_text())


def drop_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS bookings, ships"))


def verify_constraint(engine: Engine) -> None:
    with engine.connect() as conn:
        actual = conn.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'bookings'::regclass AND conname = :name"
            ),
            {"name": CONSTRAINT_NAME},
        ).scalar_one_or_none()

    if actual is None:
        raise SchemaMismatchError(
            f"Constraint {CONSTRAINT_NAME} is missing from bookings. "
            "Reset the database (python -m app.init_db --reset)."
        )
    if actual != EXPECTED_CONSTRAINT_DEF:
        raise SchemaMismatchError(
            f"Constraint {CONSTRAINT_NAME} differs from schema.sql. "
            "Reset the database (python -m app.init_db --reset).\n"
            f"  expected: {EXPECTED_CONSTRAINT_DEF}\n"
            f"  actual:   {actual}"
        )


def init_db(engine: Engine, *, reset: bool = False) -> None:
    if reset:
        drop_tables(engine)
    apply_schema(engine)
    verify_constraint(engine)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="drop the tables first")
    args = parser.parse_args()

    # stdout, not the default stderr: Railway labels anything on stderr as an error.
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stdout)
    init_db(get_engine(), reset=args.reset)
    log.info("schema applied and %s verified", CONSTRAINT_NAME)

    if args.reset:
        # Imported here: the loader depends on this package, not the other way round.
        from scripts.load_seed import load_seed

        seed_file = get_settings().seed_file
        log.info(
            "reset: reloaded %d bookings from %s", load_seed(get_engine(), seed_file), seed_file
        )


if __name__ == "__main__":
    main()
