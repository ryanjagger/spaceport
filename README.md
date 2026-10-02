# Spaceport Charter System

A two-screen booking app for the Pacific Spaceport's five charter ships. Dispatchers book a ship for a time slot; a fleet manager sees every booking by ship and can cancel upcoming ones.

The original brief is in [BRIEF.md](docs/BRIEF.md), the full design in [SPACEPORT-PRD.md](docs/SPACEPORT-PRD.md), and the build log in [PLAN.md](docs/PLAN.md).

## Run it

Requires Docker.

```
docker compose up --build
```

Open <http://localhost:8000>. The first start applies the schema and loads 3,000 seed bookings; later starts change nothing.

| Task | Command |
| --- | --- |
| Run the tests (real Postgres, separate `spaceport_test` database) | `docker compose --profile test run --rm --build test` |
| Reset all data to the seed | `docker compose down -v`, then `up` again |
| Reset without recreating the volume | `docker compose exec app python -m app.init_db --reset` |
| API docs | <http://localhost:8000/api/docs> |

The seed data is a year of history that ends in early June 2026, so today starts empty. On the Fleet dashboard, "Previous day with bookings" jumps to the seeded days.

### Live demo

<https://app-production-a9d8.up.railway.app> runs the same Dockerfile on Railway with a Railway Postgres database. It is a shared demo: anyone with the link can book or cancel.

### Local development

```
docker compose up -d db                      # Postgres on localhost:5433
cd backend && uv sync
uv run python -m app.init_db && uv run python -m scripts.load_seed
uv run uvicorn app.main:app --reload         # API on :8000

cd frontend && npm ci && npm run dev         # Vite on :5173, proxies /api to :8000
```

Backend tests outside Docker: `TEST_DATABASE_URL=postgresql://spaceport:spaceport@localhost:5433/spaceport_test uv run pytest`. The rules tests need no database: `uv run pytest tests/test_rules.py`.

Lint and format: `uv run ruff check . && uv run ruff format .` and `npm run lint` / `npm run format`.

## The rules

All times are stored in UTC and every rule is evaluated in `America/Chicago`. Intervals are half-open, `[start, end)`.

| Rule | Meaning | Enforced by |
| --- | --- | --- |
| No overlap | Two active bookings on a ship never share an instant | Postgres exclusion constraint |
| Refuel buffer | At least 30 minutes between bookings on a ship; exactly 30 is fine | The same constraint |
| Operating hours | Start at or after 6:00 AM, end by 10:00 PM Central, same day | `rules.py` |
| Grid and duration | Start on :00 or :30; 30 minutes to 8 hours in 30-minute steps | `rules.py` |
| No past bookings | A booking can't start before the server's "now" | `rules.py` |
| Cancellation | Only an active booking that hasn't started | One atomic `UPDATE` |

Overlap and buffer are one test. Extending every booking's end by 30 minutes turns "overlaps, or sits less than 30 minutes away" into a plain range overlap, which Postgres can forbid:

```sql
CONSTRAINT no_overlap_with_buffer EXCLUDE USING gist (
  ship_id WITH =,
  tsrange(start_time AT TIME ZONE 'UTC', (end_time AT TIME ZONE 'UTC') + interval '30 minutes', '[)') WITH &&
) WHERE (status = 'active')
```

The service checks for a conflict first, but only to give a precise message. Two simultaneous requests both pass that check; the constraint lets one commit and the other gets a 409. `tests/test_api_create.py::TestConcurrency` holds two requests at a barrier after the check to prove the database, not the check, decides.

## How it's built

Two containers: Postgres 16, and one app container where FastAPI serves both the API and the built React files (same origin, so no CORS).

```
backend/
  schema.sql        tables and constraints, the source of truth
  app/rules.py      every scheduling rule as a pure function (no database, no HTTP, no clock)
  app/services/     transactions: availability, create, list, cancel
  app/routers/      HTTP only
  app/errors.py     one error envelope: {"error": {"code", "message"}}
  app/init_db.py    applies schema.sql; refuses to start if the constraint is missing or different
  scripts/load_seed.py
  tests/
frontend/src/
  lib/time.ts       the only place that formats time; always America/Chicago
  api/              typed fetch client and TanStack Query hooks
  pages/            CharterPage, FleetDashboard
  components/       SlotGrid, FleetTimeline, BookingDetails
data/seed.json      generated once from the unmodified seed.py
```

### API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/ships` | The fleet |
| GET | `/api/ships/{id}/availability?date=&durationMinutes=` | Every start time for one Central day, each marked available or `past` / `booked` / `buffer` |
| GET | `/api/bookings?from=&to=&shipId=&includeCancelled=` | Bookings by Central date (at most 31 dates) |
| GET | `/api/bookings/nearest-dates?date=&includeCancelled=` | Nearest earlier and later dates with bookings |
| POST | `/api/bookings` | Create: 201, or 409 `booking_conflict` / `in_the_past`, or 422 |
| DELETE | `/api/bookings/{id}` | Cancel (soft delete): 200, or 409 `already_started` / `already_cancelled` |
| GET | `/api/time` | The server's clock; the UI takes "today" from it |
| GET | `/api/health` | Liveness and database check |

A 409 always means "the request was fine but the world moved on"; the UI shows the message and refreshes. Malformed input is a 422.

### Time zones

Every date and time means spaceport time, for every user, like an airline departure time.

- The client never builds a timestamp. It sends back the exact `start` / `end` strings the availability endpoint returned.
- Dates move through the frontend as `YYYY-MM-DD` strings, never `Date` objects.
- "Today" is the Central date of the server's clock, not the device's.
- A user outside Central also sees their own time as a hint: "9:00 PM CT (Sun 11:00 AM your time)".
- Daylight saving switches at 2:00 AM, outside operating hours, so every operating day is 16 hours. No code hard-codes an offset; tests cover 2026-11-01 and 2027-03-14.
