#!/bin/sh
# Apply the schema (and refuse to start if the constraint is wrong), load the
# seed into an empty database, then serve. Every step is safe to repeat.
set -e

python -m app.init_db
python -m app.load_seed
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
