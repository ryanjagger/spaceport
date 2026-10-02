"""Environment settings. Scheduling constants live in rules.py, not here."""

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BACKEND_DIR / "schema.sql"
STATIC_DIR = BACKEND_DIR / "static"  # the built frontend, in the Docker image

LOCAL_DATABASE_URL = "postgresql://spaceport:spaceport@localhost:5433/spaceport"
# Repo layout; the Docker image sets SEED_FILE to where it copies the file.
DEFAULT_SEED_FILE = BACKEND_DIR.parent / "data" / "seed.json"


def normalise_database_url(url: str) -> str:
    """Point SQLAlchemy at psycopg 3. Railway hands out a bare postgresql:// URL."""
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme) :]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    test_database_url: str | None
    seed_file: Path


def get_settings() -> Settings:
    test_url = os.environ.get("TEST_DATABASE_URL")
    return Settings(
        database_url=normalise_database_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL)),
        test_database_url=normalise_database_url(test_url) if test_url else None,
        seed_file=Path(os.environ.get("SEED_FILE", DEFAULT_SEED_FILE)),
    )
