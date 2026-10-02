# Spaceport Charter System

A two-screen booking app for the Pacific Spaceport's five charter ships. Dispatchers book a ship for a time slot; a fleet manager sees every booking by ship and can cancel upcoming ones.

The original brief is in [BRIEF.md](BRIEF.md), the full design in [SPACEPORT-PRD.md](SPACEPORT-PRD.md), and the build log in [PLAN.md](PLAN.md).

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

## Decisions

| Decision | Chosen | Instead of | Why |
| --- | --- | --- | --- |
| Rule enforcement | Exclusion constraint plus a service pre-check | Service check only | Check-then-insert races; the database is the only place two transactions meet |
| Database | Postgres 16 | SQLite | Exclusion constraints; SQLite would only serialise writes |
| Range type | `tsrange` of UTC values | `tstzrange` | Index expressions must be immutable, and `timestamptz + interval` is only stable |
| Availability | Server returns slots for a duration | Server returns busy intervals | Whether a start fits depends on the duration; keeps every rule server-side |
| Booking input | Duration on a 30-minute grid | Fixed 1-hour slots | The seed has 1–4 hour bookings |
| Cancellation | Soft delete, partial constraint | Hard delete | Keeps history; the slot is free again at once |
| Schema | One `schema.sql` applied at startup | Alembic | Two tables and rebuildable data; add migrations once there is data to keep |
| Data access | SQLAlchemy 2.0, sync | Async | Simpler code and tests; plenty at this scale |
| Frontend serving | FastAPI serves the Vite build | Separate Node server | Static files need no server; one origin |
| Seed | One committed `seed.json` | Generate at startup | `seed.py` anchors its dates to the day it runs |
| Server time | `/api/time` | The device clock | A wrong device clock, or a browser in Tokyo, can't change what "today" is |
| Styling | CSS modules | Tailwind | No extra dependency to justify |

## Testing

`169` backend tests against real Postgres, in three layers:

- **Rules** (`test_rules.py`, no database): buffer edges (30 allowed, 29 not), operating hours, any-offset input, DST days, slot generation, reason precedence.
- **Database** (`test_schema.py`, direct SQL): the constraint itself, including with the session timezone set to `Asia/Tokyo`, and the startup guard.
- **API** (`test_api_*.py`): every endpoint, the coordinated booking race, simultaneous cancels, and the error envelope for every failure.

The frontend has no automated tests. It was checked by hand and with a scripted browser under `America/Chicago`, `Asia/Tokyo` and `America/Los_Angeles`: booking, a 409, a lost response, cancel, keyboard-only use, focus handling in the details panel, and the narrow-screen layout. Results are in [PLAN.md](PLAN.md).

## Known limitations

- **No authentication.** Anyone can book or cancel; `pilotName` is free text. Dispatcher and manager are screens, not roles.
- **No editing.** Cancel and rebook instead.
- **Schema changes need a reset.** `schema.sql` is `IF NOT EXISTS`, so an edited constraint is not applied to an existing table. The app refuses to start rather than run with the wrong constraint.
- **"Now" is read once per request.** A request that waits on a lock across a booking's start time may still succeed.
- **The dashboard shows one day** and loads it in full; a much larger fleet would need paging.

With more time: authentication and roles, rescheduling, CI, an audit log of who cancelled what, and automated browser tests.
