# Spaceport Charter System — PRD

Oct 1, 2026 · @Ryan

## Overview

We are building a two-screen booking app for the Pacific Spaceport's 5 charter ships: dispatchers book a ship for a time slot, and a fleet manager sees every booking by ship. The backend owns every scheduling rule, and Postgres enforces the core rule so it holds even under simultaneous bookings.

**Goals**

- Book a ship for an available slot without breaking the overlap, refuel-buffer or operating-hours rules.
- Show unavailable times from a backend endpoint; the client never computes availability from raw bookings.
- Show all bookings across the fleet, organised by ship, for any date.
- Cancel an upcoming booking and free its slot.
- Start with one command (`docker compose up`) and load the seed data automatically.

**Non-goals**

- Authentication, users or roles. `pilotName` is free text.
- Editing or rescheduling a booking (cancel and rebook instead).
- Bookings that span more than one day, recurring bookings, notifications.
- Production-grade hosting (scaling, backups, monitoring). A single Railway demo deployment is in scope.

## Business rules

All times are stored in UTC and every rule is evaluated in `America/Chicago` using Python's `zoneinfo`. Intervals are half-open, `[start, end)`.

| # | Rule | Exact meaning | Enforced by |
| --- | --- | --- | --- |
| R1 | No overlap | Two active bookings on the same ship may not share any instant. | Postgres exclusion constraint + service check |
| R2 | Refuel buffer | The gap between consecutive active bookings on a ship is at least 30 minutes. Exactly 30 is allowed, 29 is not. | Same exclusion constraint |
| R3 | Operating hours | Start ≥ 6:00 AM and end ≤ 10:00 PM Central, same Central day. Ending at exactly 10:00 PM is allowed. | Service layer |
| R4 | Valid interval | `end > start`. | `CHECK` constraint + Pydantic |
| R5 | Grid and duration | Start on :00 or :30. Duration is 30 minutes to 8 hours in 30-minute steps. | Pydantic + service layer |
| R6 | No past bookings | A booking may not start before now. "Now" and "today" are computed on the server in America/Chicago. Today's remaining slots can be booked; a future date has no past slots. | Service layer |
| R7 | Pilot name | Required, trimmed, 1–100 characters. | Pydantic |
| R8 | Cancellation | Only an active booking that has not started (start\_time > now) can be cancelled. A booking in progress cannot. | Service layer |

**R1 and R2 are one test.** New booking `[s1, e1)` conflicts with existing `[s2, e2)` on the same ship when `s1 < e2 + 30 min` and `s2 < e1 + 30 min`. Overlap is the case where the gap is negative.

**The buffer applies only between bookings.** A booking at 6:00 AM needs no buffer before it, and one ending at 10:00 PM needs none after.

**Daylight saving.** Central time switches offset (−05:00 / −06:00) on 2026-11-01 and in March. The switch happens at 2:00 AM, outside operating hours, so every operating day is exactly 16 hours. The UTC instant of 6:00 AM still differs across the switch, so no code may hard-code an offset.

**Any offset, one meaning.** The API accepts timestamps in any UTC offset and converts them to America/Chicago before checking R3 and R5. On 2026-10-02 (CDT, −05:00): `2026-10-02T16:30:00+05:30` is 6:00 AM CT and valid; `2026-10-02T17:00:00+05:45` is 6:15 AM CT and rejected as off-grid. Examples must carry a date, because in winter (CST, −06:00) the same offsets map an hour differently. Seconds and fractions must be zero, not just the minutes on :00 or :30.

**Days are independent.** A booking ends by 10:00 PM, so its buffer ends by 10:30 PM, 7.5 hours before the next opening. No booking can affect another day's slots, so availability reads only the selected Central date's bookings.

**What "now" means.** Each service operation reads the clock once and passes that timezone-aware reference time into the pure rule functions; tests inject a fixed clock. Creating a booking allows `start == now`; cancelling requires `start > now`. Eligibility is checked at that moment in the operation, not at commit time, so a request that waits on a lock and crosses the start boundary may still succeed; that is acceptable for this demo. Availability returns `serverNow`, and the UI uses it rather than the device clock, so a wrong device clock can't mislead it.

**Booked versus buffer.** The service tests the whole candidate interval. If it overlaps an active booking at all, the slot is `booked`, even if it starts in free time. It is `buffer` only when it overlaps no booking but falls inside one's 30-minute margin.

## Time zones

Every date and time in the app means spaceport time (`America/Chicago`), for every user, wherever they are. The spaceport is a physical place, so its local time is the reference, as with airline departure times.

**Rules**

1. Dates move through the frontend as plain `YYYY-MM-DD` strings, never JavaScript `Date` objects. The backend reads them as Central dates.
2. "Today" is the Central date of the server's latest serverNow, formatted with `Intl.DateTimeFormat` and `timeZone: 'America/Chicago'`, never from `new Date()` alone.
3. All time display goes through one helper, `lib/time.ts`, which always passes `timeZone: 'America/Chicago'` and labels times "CT".
4. The frontend never builds a timestamp. A booking request sends the exact `start`/`end` strings of the slot the backend returned.
5. The backend ignores the server's own timezone: it stores UTC and evaluates rules in `America/Chicago`.

**Local-time hint.** When the browser's timezone is not Central, slot buttons and booking details add the user's local time as a secondary line, e.g. "8:00 AM CT (3:00 PM your time)", with the date when it differs, e.g. "Fri 9:00 PM CT (Sat 11:00 AM your time)".

**Bugs these rules prevent**

| Bug | Cause | Prevented by |
| --- | --- | --- |
| Wrong default date near midnight | Browser "today" differs from Central "today" | Rule 2 |
| Picked date shifts by one day | `toISOString()` converts to UTC first | Rule 1 |
| Slots shown in the user's local time | Formatting without a `timeZone` option | Rule 3 |
| Booking lands an hour off | Client-built timestamp with the wrong offset | Rule 4 |

**Verification.** Override the browser timezone in Chrome DevTools (Sensors) to `Asia/Tokyo` and `America/Los_Angeles`, then book a slot and view the dashboard after 11:00 PM Central, when Tokyo is already on the next day.

## User flows

**Book a ship**

1. Pick a ship, a Central date (defaults to today) and a duration (defaults to 1 hour).
2. The app calls the availability endpoint and shows the day's start times every 30 minutes, 6:00 AM to the last start that fits before 10:00 PM. Unavailable times are greyed out, each labelled with a short visible reason (booked, refuel buffer, past). A caption above the grid explains the cut-off, e.g. "Last start 9:00 PM for a 1-hour charter (spaceport closes 10:00 PM CT)".
3. Pick an available start time, enter a pilot name, confirm.
4. Success: an inline confirmation banner above the grid with the booking's times, and the grid refreshes.
5. A 409 (someone booked it first, or the start time has passed): an inline message, and the grid refreshes automatically. The form keeps the pilot name.

**View the fleet**

1. Open the dashboard. It shows today, one timeline row per ship, 6:00 AM–10:00 PM.
2. Move with previous/next day buttons or a date picker.
3. An empty day shows "No bookings on this day" with "Previous day with bookings" and "Next day with bookings" links, each disabled when there is none in that direction.
4. A "Show cancelled" toggle adds cancelled bookings to the grouped list, marked Cancelled. The timeline always shows active bookings only, so a cancelled booking can never hide the one that replaced it.

**Cancel a booking**

1. Click a booking on the dashboard to open its details: ship, pilot, times, status.
2. Upcoming active bookings show a Cancel button; it asks for confirmation and is disabled while the request is in flight.
3. On success the booking disappears (or moves to the list's cancelled entries with the toggle on), and that ship's availability is refreshed.
4. Past, started or already cancelled bookings show no Cancel button. The API rejects them anyway (409).

## Architecture

Two containers: Postgres, and one app container where FastAPI serves both the API and the built React files. Same origin, so no CORS. Any non-API path that isn't a static file returns index.html, so refreshing /fleet works.

&#91;embedded content: architecture · 2 containers\]

Requests flow from routers to services, which call the pure rules and then Postgres; the exclusion constraint is the final guard against double booking.

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React + TypeScript, Vite, React Router | Two typed screens; Vite builds to static files |
| Data fetching | TanStack Query | Caching and invalidation after book/cancel |
| Styling | Plain CSS modules | No extra dependency to justify |
| API | FastAPI, Pydantic v2 | Validation and OpenAPI docs for free |
| Data access | SQLAlchemy 2.0 (sync), psycopg 3 | Queries and transactions only; schema.sql owns the schema. Sync is simpler to read and test |
| Schema | One schema.sql, applied at startup | Every database rule in one readable file, including `btree_gist` |
| Database | Postgres 16 | Exclusion constraints enforce R1–R2 under concurrency |
| Runtime | Docker Compose, multi-stage Dockerfile | One command, one URL (`localhost:8000`) |

**Layering.** Routers parse HTTP and map errors to status codes. The service layer runs the rules and transactions. `rules.py` is pure functions with no database or HTTP, so every edge case is unit-testable.

**Code quality and reproducibility**

- Python: Ruff for linting and formatting (`ruff check`, `ruff format`). Dependencies managed with uv and locked in `uv.lock`.
- Frontend: ESLint and Prettier (`npm run lint`, `npm run format`). Dependencies locked in `package-lock.json` and installed with `npm ci`.
- Docker base images pinned to a patch version and Debian release, currently `python:3.12.15-slim-bookworm`, `postgres:16.15-bookworm` and `node:22.23.3-bookworm-slim`, so a reviewer's build matches ours. Digests would be stricter but are overkill here; `uv.lock` pins Python packages, not the base image.

**Repo layout**

```
backend/
  schema.sql         # tables, constraints, btree_gist (source of truth)
  app/
    main.py          # FastAPI app, mounts /api and the static frontend
    config.py        # env settings only (DATABASE_URL, TEST_DATABASE_URL, PORT)
    db.py            # engine + session
    init_db.py       # applies schema.sql
    models.py        # Ship, Booking (mirror schema.sql)
    schemas.py       # Pydantic models, camelCase aliases
    rules.py         # pure rules + fixed constants (hours, grid, 30-min buffer)
    services/        # bookings.py, availability.py
    routers/         # ships.py, bookings.py, health.py
  scripts/load_seed.py
  tests/
frontend/
  src/
    api/             # typed fetch client + query hooks
    pages/           # CharterPage, FleetDashboard
    components/      # SlotGrid, FleetTimeline, BookingDetails
    lib/time.ts      # Central-time formatting helpers
data/seed.json
seed.py
Dockerfile
docker-compose.yml
railway.toml
README.md
```

## Data model

Cancellation is a soft delete: a booking keeps its row and gets `status = 'cancelled'`, and the exclusion constraint only covers active bookings, so a cancelled slot is immediately bookable again.

**ships**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer, PK | Seed ids 1–5 kept as-is |
| `name` | text, not null, unique |  |

**bookings**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | bigint identity, PK | Assigned on insert (seed has no ids) |
| `ship_id` | integer, FK → ships, not null |  |
| `pilot_name` | text, not null | 1–100 chars, trimmed |
| `start_time` | timestamptz, not null | UTC |
| `end_time` | timestamptz, not null | UTC |
| `status` | text, not null, default `'active'` | `active` or `cancelled` (CHECK) |
| `created_at` | timestamptz, default `now()` |  |
| `cancelled_at` | timestamptz, null | Set on cancel |

**Constraints**

The schema lives in one file, `backend/schema.sql`, applied on every startup. Every statement is `IF NOT EXISTS`, so re-running it on an existing database changes nothing. That makes it safe for a fresh database, not a changed one: an edited constraint on an existing table is silently skipped. A schema change means resetting the database (locally docker compose down -v; on Railway, recreate the Postgres service). As a guard on every boot, init\_db.py compares the constraint's full definition (pg\_get\_constraintdef on the bookings table) with the expected text and refuses to start if it is missing or different. The constraints sit inside `CREATE TABLE` because `ALTER TABLE ADD CONSTRAINT` has no `IF NOT EXISTS` form.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS ships (
  id   integer PRIMARY KEY,
  name text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bookings (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ship_id      integer NOT NULL REFERENCES ships(id),
  pilot_name   text NOT NULL CHECK (char_length(btrim(pilot_name)) BETWEEN 1 AND 100),
  start_time   timestamptz NOT NULL,
  end_time     timestamptz NOT NULL,
  status       text NOT NULL DEFAULT 'active',
  created_at   timestamptz NOT NULL DEFAULT now(),
  cancelled_at timestamptz,
  CONSTRAINT valid_interval CHECK (end_time > start_time),
  CONSTRAINT valid_status CHECK (status IN ('active', 'cancelled')),
  CONSTRAINT no_overlap_with_buffer EXCLUDE USING gist (
    ship_id WITH =,
    tsrange(
      start_time AT TIME ZONE 'UTC',
      (end_time AT TIME ZONE 'UTC') + interval '30 minutes',
      '[)'
    ) WITH &&
  ) WHERE (status = 'active')
);
```

The SQLAlchemy models describe these tables for queries; they never create them. A test checks the models' columns match the database.

Extending every booking's end by 30 minutes turns R1 + R2 into a plain range overlap: `[s1, e1+30)` and `[s2, e2+30)` intersect exactly when the combined test in Business rules fails. Extending only the end is enough, whichever booking comes first.

**Why `tsrange` of UTC values, not `tstzrange`.** Postgres only accepts immutable expressions in an index, and `timestamptz + interval` is only stable: its result can depend on the session timezone. The first version, `tstzrange(start_time, end_time + interval '30 minutes')`, fails with "functions in index expression must be marked IMMUTABLE" (verified on Postgres 16.15). Converting to UTC first (`AT TIME ZONE 'UTC'`) gives a plain `timestamp`, and `timestamp + interval` is immutable. The columns stay `timestamptz`. Verified on 16.15: a gap of exactly 30 minutes is accepted, 29 is rejected, other ships and cancelled rows don't conflict, and the result is the same with the session timezone set to `Asia/Tokyo`.

The constraint is authoritative. The service's pre-check exists only to return a precise message and uses the same expression (`ship_id = :id AND status = 'active' AND tsrange(start_time AT TIME ZONE 'UTC', (end_time AT TIME ZONE 'UTC') + interval '30 minutes', '[)') && :candidate`). At 3,000 rows Postgres will usually scan the table for it, which is fine.

The 30-minute buffer, operating hours and grid are fixed constants in `rules.py`, not configuration: the SQL hard-codes the buffer, and the startup guard (below) checks the constraint's definition, so the two can't drift apart.

Operating hours (R3) stay in the service layer: a timezone-aware CHECK is possible but harder to read and test than Python.

**Why soft delete.** The manager can still see what was cancelled, and a cancelled booking stays on record instead of vanishing. The cost is one extra `WHERE status = 'active'` in reads, which the service layer applies by default.

## API

All endpoints live under `/api`, use camelCase JSON (Pydantic alias generator; Python stays snake\_case), and return timestamps as ISO 8601 with offset. Request timestamps without an offset are rejected (422).

| Method | Path | Purpose | Responses |
| --- | --- | --- | --- |
| GET | `/api/ships` | List the fleet | 200 |
| GET | `/api/ships/{id}/availability?date=YYYY-MM-DD&durationMinutes=60` | Slot grid, lastStart and serverNow for one Central day | 200, 404 ship, 422 bad params |
| GET | `/api/bookings?from=YYYY-MM-DD&to=YYYY-MM-DD&shipId=&includeCancelled=false` | Dashboard data; `from`/`to` required, inclusive Central dates, from ≤ to, at most 31 dates; omit shipId when unused; an unknown shipId → 404 | 200, 422 |
| GET | `/api/bookings/nearest-dates?date=YYYY-MM-DD`&includeCancelled=false | Nearest earlier and later Central dates with active bookings, as { previous, next }; either may be null | 200 |
| POST | `/api/bookings` | Create a booking | 201, 404 ship, 409 conflict, 422 invalid |
| DELETE | `/api/bookings/{id}` | Cancel (soft delete); returns the updated booking | 200, 404, 409 started/cancelled |
| GET | `/api/time` | The server's clock as `{ serverNow, timezone }`; both pages take "today" from it | 200 |
| GET | `/api/health` | Liveness + database check for Railway | 200, 503 |

**Ships response**

```json
[ { "id": 1, "name": "USS Wanderer" }, { "id": 2, "name": "Nostromo" } ]
```

An empty array is valid (a fresh database before the seed loads); the charter page then shows "No ships available".

**Bookings list.** The dashboard's day view always sends `from` = `to` = the date shown. `includeCancelled` on `nearest-dates` follows the dashboard's "Show cancelled" toggle, so a day with only cancelled bookings isn't skipped while they're visible.

**Availability response**

```json
{
  "shipId": 3,
  "date": "2026-10-02",
  "timezone": "America/Chicago",
  "serverNow": "2026-10-01T21:44:12-05:00",
  "durationMinutes": 60,
  "lastStart": "2026-10-02T21:00:00-05:00",
  "slots": [
    { "start": "2026-10-02T06:00:00-05:00", "end": "2026-10-02T07:00:00-05:00", "available": true, "reason": null },
    { "start": "2026-10-02T09:00:00-05:00", "end": "2026-10-02T10:00:00-05:00", "available": false, "reason": "buffer" }
  ]
}
```

- `slots` lists every start on the 30-minute grid whose end fits by 10:00 PM; `lastStart` feeds the caption above the grid.
- `reason` is one of `past`, `booked`, `buffer`. When several apply, the first in that order wins: a slot that is past and inside a buffer reports `past`.
- The service loads that ship's active bookings starting on the selected Central date (other days cannot affect it; see Business rules) and runs `rules.py` per slot: at most 32 slots × about 10 bookings.
- There is no `blocked` field: no screen draws bookings from this endpoint, so it returns only what the charter page renders.

**Create request**

```json
{ "shipId": 3, "pilotName": "Naomi Nagata", "startTime": "2026-10-02T06:00:00-05:00", "endTime": "2026-10-02T07:00:00-05:00" }
```

The client sends start and end (not start + duration) so the API is general; the service still checks R5.

**Create validation.** The pilot name is trimmed before its length is checked. Unknown fields are rejected (422). `startTime`/`endTime` must carry an offset and have zero seconds and fractions.

**Booking response** — one shape for create (201), cancel (200) and the bookings list:

```json
{
  "id": 812,
  "shipId": 3,
  "pilotName": "Naomi Nagata",
  "startTime": "2026-10-02T06:00:00-05:00",
  "endTime": "2026-10-02T07:00:00-05:00",
  "status": "active",
  "createdAt": "2026-10-01T21:44:12-05:00",
  "cancelledAt": null
}
```

- `id` is a JSON number. Timestamps are returned in Central offset.
- Ship names are not embedded; the frontend resolves them from `/api/ships`.
- The bookings list is a plain array, ordered by `shipId`, then `startTime`, then `id`.

**Error shape** — every 4xx returns `{ "error": { "code": "booking_conflict", "message": "…" } }`. Codes: `booking_conflict`, `outside_operating_hours`, `in_the_past`, `invalid_duration`, `not_on_grid`, `already_cancelled`, `already_started`, `not_found`, `validation_error`.

**Every error uses that envelope**, including FastAPI's own validation errors and framework errors (custom handlers for `RequestValidationError` and `HTTPException`, code `validation_error` / `not_found`). An unhandled exception returns 500 with code `internal_error` and a generic message, never a stack trace. If a response isn't JSON (a proxy error page), the frontend shows a generic "Something went wrong" message.

**Conflict handling.** The exclusion constraint is authoritative; the service's pre-check exists only to return a precise message. If a concurrent insert wins the race, Postgres raises `23P01` (exclusion violation) and the router maps exactly that code to 409 `booking_conflict`; any other integrity error stays a 500. A concurrent cancel can occasionally make the pre-check return a 409 for a slot that had just freed up. That is acceptable: the two requests overlapped, and either outcome is a valid ordering.

**State-dependent errors are 409.** `booking_conflict`, `in_the_past`, `already_started` and `already_cancelled` all return 409, because the request was valid but the world moved on. The frontend handles every 409 the same way: show the message and refresh availability. Malformed input stays 422.

**Cancel is one atomic statement.** `UPDATE bookings SET status = 'cancelled', cancelled_at = now() WHERE id = :id AND status = 'active' AND start_time > :now RETURNING *`. If no row returns, the service looks the booking up to choose 404, `already_cancelled` or `already_started`. Two simultaneous cancels cannot both succeed.

## Frontend

Two routes: `/` (Charter a Ship) and `/fleet` (Fleet Manager Dashboard), with a top nav between them. Every time is shown in Central regardless of the browser's timezone, via `Intl.DateTimeFormat` with `timeZone: 'America/Chicago'`, and labelled "CT".

**Charter a Ship (`/`)**

- Controls: ship select, date picker (min = today, Central), duration select (30 min – 8 h, 30-minute steps).
- `SlotGrid`: one button per slot from the availability response. Available = selectable; unavailable = disabled with its reason as visible text on the button ("Booked", "Refuel", "Past"), not only on hover, so keyboard and touch users see it.
- Booking panel: selected time range, pilot name input, Book button. Disabled until a slot and name are set, and while the request is in flight (label changes to "Booking…"), so a double-click can't send a second request.
- Query key `['availability', shipId, date, duration]`; invalidated after book and cancel.

**Selection and freshness**

- Changing ship, date or duration clears the selected slot but keeps the pilot name. A selected slot must exist and be available in the current availability response; after any refresh, a missing or unavailable selection is cleared.
- After a successful create or cancel, invalidate availability for that ship and date across every duration (query-key prefix `['availability', shipId, date]`), the bookings list, and `nearest-dates`.
- A 409 on cancel refreshes the bookings list and the open details panel, not just availability.
- Queries refetch on window focus and reconnect. Today's availability also refetches every 60 seconds while visible; the server still makes the final decision.
- "Today" and the date picker's minimum come from the latest `serverNow`, so a page left open past midnight Central moves to the new day.
- Booking and cancel requests are never retried automatically. If a request fails without a response (timeout, network drop), show "We couldn't confirm whether this booking succeeded" and refresh availability and bookings before offering to try again. A 409 is a definite answer and is handled as above.

**Fleet Manager Dashboard (`/fleet`)**

- Header: date picker, previous/next day, Today, "Show cancelled" toggle. The day view requests bookings with from = to = the date shown.
- `FleetTimeline`: a 6:00 AM–10:00 PM axis, one row per ship. Each booking is a block positioned by its Central start/end, labelled with pilot and times. The 30-minute buffer after each booking is drawn as a hatched strip, so the refuel rule is visible. Only active bookings get the strip, and it is clipped at 10:00 PM.
- Below the timeline: the same bookings as a list grouped by ship, for readability and screen readers. On narrow screens the list is the primary view and the timeline is hidden.
- Clicking a booking opens `BookingDetails` with a Cancel button for upcoming active bookings.
- Empty state with previous/next "day with bookings" links, relative to the date being viewed.
- Query key `['bookings', from, to, includeCancelled]`.

**States everywhere**: loading skeleton, API error message with Retry, empty state. Errors show the API's `message`, never a raw status code.

**Accessibility.** Unavailable reasons are visible text, not tooltips. The booking details panel moves focus into itself when opened and returns it to the booking that opened it when closed. Success and error messages are in an `aria-live` region so screen readers announce them.

**Shared-demo notice.** A slim banner on both pages: "Shared demo: anyone with this link can book or cancel. Data resets periodically." Dispatcher and manager are screens, not permission levels.

## Seed data

`seed.py` always produces data that obeys the structural scheduling rules (hours, grid, overlap, buffer) but ends roughly four months before the day it is generated, so the app must handle empty days well. Its properties, whatever the run date:

| Property | Value | Consequence |
| --- | --- | --- |
| Volume | 600 bookings per ship, 3,000 total; about 2.5 per ship-day, at most 5 | No performance concerns |
| Date range | Starts at the run date − 365 days; stops at 600 per ship (about 8 months in) or at run date + 30 days, whichever comes first | In practice the cap hits first, so there are never future bookings. Generated 2026-10-01, the data ends late May to early June 2026 |
| Start times | First booking of a day at 6:30 AM at the earliest (never 6:00); all starts on :00 or :30 | Fits the 30-minute grid |
| Durations | 60, 90, 120, 150, 180 or 240 minutes; never 30 and never over 4 hours | New bookings may be 30 minutes to 8 hours, a wider range than the seed |
| Gaps | 30-minute buffer plus an idle gap of at least 30 minutes, so at least 60 minutes | Loads cleanly under the exclusion constraint |
| Timestamps | ISO 8601 with offset, built with zoneinfo; both −05:00 and −06:00 | Parsed as aware datetimes; DST is exercised |
| IDs | Bookings have none | The database assigns them |
| Determinism | RNG seeded with 42, but dates anchored to datetime.now() | A different run day shifts every date |

**Loading**

- Commit one generated `data/seed.json` so every reviewer sees the same dashboard. `seed.py` stays in the repo unchanged.
- `scripts/load_seed.py` runs at container start, right after the schema is applied. It takes a Postgres advisory lock (so two instances starting at once can't both load), then inserts ships with their ids and all bookings in one transaction, and does nothing if the bookings table already has rows. A failed load commits nothing, so the next start retries it in full. Before inserting, every row is checked with rules.py for operating hours, grid and duration, because the database constraint only covers overlap and buffer and the "days are independent" rule relies on valid hours. Historical import is exempt from R6 (no bookings in the past).
- Seed rows go through the same constraint as API bookings; a violation fails the load loudly rather than being skipped.
- An env var `SEED_FILE` lets someone load a freshly generated file instead.

## Testing

Tests use their own small fixtures, never the seed file, and a fixed injected clock. They run against a real Postgres because the key rule lives in the database.

**Isolation.** Tests use a separate database, `spaceport_test`, on the same Postgres server, given by `TEST_DATABASE_URL`; the `db` service creates it with an init script. Destructive fixtures refuse to run unless the database name ends in `_test` and differs from `DATABASE_URL`. A compose `test` service, under a `test` profile, is built from a `test` stage of the Dockerfile that adds dev dependencies and the `tests/` folder. It runs `pytest` directly: no seed load and no web server.

The test database is built from the same `schema.sql`, so tests run against exactly the schema Railway runs. One test queries `pg_constraint` to assert `no_overlap_with_buffer` exists, so a missing constraint fails loudly instead of hiding behind the service-layer check.

**Unit tests (`rules.py`, no database)**

- Buffer: a gap of exactly 30 minutes allowed; 29 rejected; overlap rejected; end-to-start touching rejected.
- Hours: start at 6:00 AM and end at 10:00 PM accepted; a booking ending 10:30 PM rejected; 5:30 AM start rejected; a 30-minute booking at 6:30 AM accepted.
- Offsets, dated: `2026-10-02T16:30:00+05:30` (6:00 AM CDT) accepted; `2026-10-02T17:00:00+05:45` (6:15 AM CDT) rejected as off-grid; the same instant written in −05:00 and −04:00 treated identically; non-zero seconds rejected.
- Slot generation on a normal day, on 2026-11-01 (DST ends) and on 2027-03-14 (DST starts): 6:00 AM Central maps to the right UTC instant each time.
- Reasons: a slot that is both past and inside a buffer reports `past`; a slot starting in free time but running into a booking reports `booked`; one that only touches a booking's 30-minute margin reports `buffer`.
- "Now": creating with `start == now` allowed; cancelling with `start == now` rejected.
- Durations off the grid, under 30 minutes or over 8 hours rejected.

**Integration tests (API + Postgres)**

- Create → 201 with the booking response; the same slot again → 409 `booking_conflict`; a start that has passed → 409 `in_the_past`.
- Coordinated race: two create requests for overlapping slots on separate connections, held at a barrier until both have passed the service pre-check, then released to insert. Exactly one 201 and one 409, which proves the constraint, not the pre-check, decided.
- Two simultaneous cancels of the same booking: exactly one 200, one 409.
- After a request fails on the exclusion constraint, the next request on that worker succeeds (the session was rolled back).
- Availability marks the right slots `past` / `booked` / `buffer` and returns `lastStart` and `serverNow`; a new booking changes it.
- Cancel → 200; the freed slot can be booked; cancel a booking in progress → 409 `already_started`.
- Bookings list: `includeCancelled=true` returns cancelled bookings, the default doesn't; `from > to` → 422; ordering is ship, start, id. `nearest-dates` returns the right previous/next dates.
- Every error, including FastAPI validation errors and an unhandled exception, comes back in the error envelope.
- `init_db` refuses to start when the constraint is missing or its definition differs.
- Naive timestamp → 422; unknown field → 422; unknown ship → 404; pilot name of 101 characters after trimming rejected by the API and by the database CHECK.

**Database tests (direct SQL, no API)**

- Overlap and a 29-minute gap rejected; exactly 30 minutes accepted.
- Other ships and cancelled rows never conflict.
- Results identical with the session timezone set to `Asia/Tokyo`.

**Frontend**: no automated tests by default (agreed). Before submitting, walk this manual checklist:

- [ ] Book, cancel and view flows work end to end, including a 409 and a simulated network failure.
- [ ] Changing ship, date or duration clears the selection and keeps the pilot name.
- [ ] Unavailable reasons are readable without hovering, and every control works by keyboard.
- [ ] Details panel focus moves in and back; messages are announced by a screen reader.
- [ ] Narrow screen shows the grouped list; cancelled bookings appear only in the list.
- [ ] Browser timezone set to Tokyo and Los Angeles: dates and times unchanged; local-time hint shows the date when it differs.

## Running it

A reviewer runs `docker compose up --build` and opens `http://localhost:8000`.

- **`db`**: stock `postgres:16`.\<minor>-bookworm (pinned; see Code quality), a named volume, and a `pg_isready` healthcheck.
- **`app`**: multi-stage Dockerfile. Stage 1 (Node) runs `npm ci && npm run build`. Stage 2 (Python) installs the backend and copies the built files to `/app/static`. It waits for a healthy `db`, then the entrypoint runs `python -m app.init_db`, then `load_seed.py`, then `exec uvicorn`.
- **Local development**: Postgres from compose, `uvicorn --reload` for the API, and the Vite dev server with a proxy from `/api` to `:8000` for hot reload.
- **Tests**: `docker compose --profile test run --rm test`.
- **Reset data**: `docker compose down -v`.

## Deployment (Railway)

A live demo runs on Railway as one Railway project with two services: the app, built from the repo's Dockerfile, and a Railway Postgres database. The Hobby plan subscription is $5/month and includes $5 of usage. Actual cost depends on usage; one small app plus a small Postgres should stay near that, which we confirm on Railway's usage page after the first week. New accounts start with a one-time $5 trial credit.

**Setup**

1. Create a Railway project, add a Postgres database, and add a service from the GitHub repo. Railway builds the existing Dockerfile; no separate frontend service.
2. On the app service, set `DATABASE_URL` to reference the Postgres service's connection URL, using Railway's variable reference.
3. Generate a public domain for the app service. Pushes to `main` redeploy automatically.
4. On the first deploy, confirm `CREATE EXTENSION btree_gist` succeeds in the deploy log; it is the first statement of schema.sql. It ships with standard Postgres, but Railway's docs don't list it explicitly.

**Tooling.** The Railway CLI and the Railway MCP server will both be available during implementation. Use them for the setup steps above (create the project and services, set variables, generate the domain), to trigger deploys, and to read build and deploy logs, including the `btree_gist` check. Any setting changed through them must also be written down here or in `railway.toml`, so the deployment can be rebuilt without them.

**What the app must do for this**

- Read `PORT` from the environment and pass it to uvicorn (`--host 0.0.0.0 --port $PORT`), defaulting to 8000 locally.
- Normalise the database URL: Railway provides `postgresql://…`, and `config.py` rewrites the scheme to `postgresql+psycopg://` for SQLAlchemy.
- Expose `GET /api/health` (checks a `SELECT 1`), and point Railway's health check at it via a committed `railway.toml`.
- Keep startup safe to repeat: schema.sql and the idempotent seed load run on every deploy, as they do locally.

**Scope.** One instance, no autoscaling, backups or monitoring. Anyone with the URL can read pilot names, create bookings and cancel any upcoming booking. The app shows a shared-demo notice, the seed uses fictional names, and python -m app.init\_db --reset drops the tables, reapplies schema.sql and reloads the seed. The README leads with `docker compose up` and lists the Railway URL as a bonus, so the app can always be reviewed locally.

## Build order

Build from the database outward, so each step rests on tested work. Each step ends with a check that must pass before the next starts.

1. **Skeleton.** `docker-compose.yml`, Dockerfile, `schema.sql`, `init_db.py`, `/api/health`. Check: `docker compose up` answers `/api/health`, and the constraint test passes.
2. **Rules.** `rules.py` and its unit tests: buffer edges, operating hours, grid, durations, DST dates. Check: all unit tests green.
3. **Seed.** `seed.json` committed, `load_seed.py`. Check: 3,000 bookings load; a second run inserts nothing.
4. **Booking API.** Ships, availability, create booking with 409 mapping. Check: integration tests, including the concurrent-booking test.
5. **Read and cancel API.** Bookings list, `nearest-dates`, cancel. Check: integration tests for each.
6. **Frontend shell.** Routing, API client, `lib/time.ts`. Check: both pages load and show Central times.
7. **Charter page.** Controls, slot grid, caption, booking panel, 409 handling. Check: the Book a ship flow works end to end.
8. **Dashboard.** Timeline, grouped list, empty-state links, details and cancel. Check: the View and Cancel flows work end to end.
9. **Time-zone pass.** DevTools override to Tokyo and Los Angeles. Check: dates and times unchanged.
10. **README.** Setup, decision log, known limitations. Check: a fresh clone runs with one command.
11. **Railway.** Deploy, domain, `btree_gist` check. Check: the live URL books and cancels.

## Decision log

Each decision with the alternative we rejected, for the README and the technical call.

| Decision | Chosen | Rejected | Why |
| --- | --- | --- | --- |
| Rule enforcement | Postgres exclusion constraint + service pre-check | Service check only | A check-then-insert races; the database is the only place two transactions meet |
| Database | Postgres 16 | SQLite with `BEGIN IMMEDIATE` | Exclusion constraints; SQLite would serialise writes instead |
| Containers | Compose: `db` + `app` | One container running both | One process per container; clean restarts and shutdown |
| Frontend serving | FastAPI serves the Vite build | Separate Node server | Static files need no server; same origin, no CORS |
| Backend | FastAPI + Pydantic | Django + DRF | Small API, typed schemas, OpenAPI docs |
| Data access | SQLAlchemy 2.0, sync, psycopg 3 | Async + asyncpg; raw SQL | Simpler code and tests; async not needed at this scale |
| Time storage | UTC `timestamptz`, rules in `America/Chicago` | Store local times | Unambiguous instants; DST handled in one place |
| Booking input | Duration + 30-minute start grid | Fixed 1-hour slots | Fits the seed's 1–4 hour bookings |
| Availability | Backend returns slots for a duration | Backend returns busy intervals only | Whether a start fits depends on duration; keeps rules server-side |
| Cancellation | Soft delete, partial constraint | Hard delete | Keeps history; freed slot reusable at once |
| Seed data | Commit one `seed.json` | Generate at startup | `seed.py` depends on the run date |
| API casing | camelCase JSON | snake\_case JSON | Matches the spec and the seed |
| Styling | CSS modules | Tailwind | Fewer dependencies to justify |
| Hosting | Railway: Dockerfile service + Railway Postgres | Render free + Neon free Postgres | Always on, so no \~1-minute cold start on the reviewer's first click; same shape as Compose |
| Schema management | One schema.sql, IF NOT EXISTS, applied at startup | Alembic migrations | Migration overhead isn't justified for disposable demo data: two tables, one schema, everything rebuildable from the seed. A schema change after deploy means resetting the Railway database. Add Alembic once there is data to preserve. |
