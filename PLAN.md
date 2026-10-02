# Spaceport — Implementation Plan

Derived from `SPACEPORT-PRD.md` (the PRD stays the source of truth; this file only orders the work).
One step at a time, in order. A step is done when every box is ticked **and** its gate passes.
Status: `[ ]` todo · `[~]` in progress · `[x]` done.

## Working rules

- Do not start step N+1 until step N's gate is green. Paste the gate's output under the step's **Result** line.
- If the PRD and reality disagree (e.g. a version, an API that behaves differently), fix the PRD in the same step and note it under **Deviations** at the bottom.
- Constants (hours, grid, buffer) live only in `rules.py` and `schema.sql`. No hard-coded UTC offsets anywhere.
- Backend: `ruff check` + `ruff format --check` clean at the end of every backend step. Frontend: `npm run lint` clean at the end of every frontend step.

## Assumptions I'm making (change any of these before I start)

| # | Topic | Default |
| --- | --- | --- |
| A1 | Existing `README.md` is the take-home brief | Move it to `BRIEF.md` in step 10; the new README replaces it |
| A2 | `data/seed.json` | Generated once from the unmodified `seed.py` on 2026-10-01 and committed |
| A3 | `nearest-dates` says "active bookings" but takes `includeCancelled` | Active only by default; cancelled count too when the flag is true |
| A4 | Bookings list date filter | By the Central date of `start_time` (bookings never span days) |
| A5 | Unknown `/api/*` path | 404 in the error envelope, never the `index.html` fallback |
| A6 | Race test "barrier" | An injectable no-op hook in the booking service between pre-check and insert; tests replace it with a `threading.Barrier` |
| A7 | Image pins | Resolve the current `python:3.12.x-slim-bookworm`, `postgres:16.x-bookworm`, `node:22.x-bookworm-slim` patch tags in step 1 and write them into the PRD |
| A8 | Frontend checklist | I walk it with Chrome DevTools (timezone emulation, network throttling/offline) and record results; no automated frontend tests |
| A9 | Commits | One commit per completed step, on a `build` branch, only once you say to commit. Authored as Ryan Jagger (the configured git user), no Claude attribution or co-author lines |
| A10 | Railway (step 11) | Creates billable, public resources — I stop and confirm before creating anything |

---

## Step 1 — Skeleton

- [x] `backend/pyproject.toml` (uv, Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, psycopg 3, uvicorn; dev: pytest, httpx, ruff) + `uv.lock`
- [x] `backend/schema.sql` exactly as in the PRD (extension, `ships`, `bookings`, three constraints)
- [x] `app/config.py`: `DATABASE_URL`, `TEST_DATABASE_URL`, `PORT`, `SEED_FILE`; rewrite `postgresql://` → `postgresql+psycopg://`
- [x] `app/db.py`: engine + session dependency (rollback on error)
- [x] `app/init_db.py`: apply `schema.sql`; compare `pg_get_constraintdef` for `no_overlap_with_buffer` with the expected text and refuse to start on missing/different; `--reset` flag (drop, reapply, reload seed — seed part wired in step 3)
- [x] `app/models.py`: `Ship`, `Booking` mirroring the schema (never `create_all`)
- [x] `app/main.py` + `routers/health.py`: `GET /api/health` → 200 / 503 on `SELECT 1`
- [x] `Dockerfile`: python runtime stage, `test` stage with dev deps + `tests/`
- [x] Entrypoint: `init_db` → (seed, step 3) → `exec uvicorn --host 0.0.0.0 --port ${PORT:-8000}`
- [x] `docker-compose.yml`: `db` (pinned image, volume, `pg_isready`, init script creating `spaceport_test`), `app` (waits for healthy db), `test` (profile `test`)
- [x] `tests/conftest.py`: test DB from `schema.sql`; destructive fixtures refuse unless name ends `_test` and differs from `DATABASE_URL`
- [x] Database tests (direct SQL): overlap rejected; 29-min gap rejected; exactly 30 accepted; other ship / cancelled row don't conflict; same results with session TZ `Asia/Tokyo`; `pg_constraint` has `no_overlap_with_buffer`; pilot name 101 chars rejected by CHECK
- [x] Test: models' columns match the database
- [x] Test: `init_db` refuses to start when the constraint is missing or altered

**Gate:** `docker compose up --build` → `curl localhost:8000/api/health` is 200; `docker compose --profile test run --rm test` green.
**Result (2026-10-01):** passed. `GET /api/health` → `{"status":"ok"} 200`, also after an app restart (schema re-applied, no change). Test service: `27 passed`. Ruff clean.

## Step 2 — Rules

- [x] `app/rules.py`, pure, no DB/HTTP; every function takes aware datetimes and an explicit `now`
  - constants: `TZ`, open 06:00, close 22:00, grid 30, buffer 30, duration 30–480
  - `validate_interval` → raises typed errors mapped to `not_on_grid`, `invalid_duration`, `outside_operating_hours`, `in_the_past` (converts any offset to Central first; seconds/micros must be zero; same Central day)
  - `conflicts(candidate, existing)` — the combined R1+R2 test
  - `day_slots(date, duration)` and `last_start` — built via `zoneinfo`, DST-safe
  - `slot_reason(slot, bookings, now)` → `past` > `booked` > `buffer` > `None`
  - `can_cancel(booking, now)` — strict `start > now`
- [x] Unit tests, one per bullet in PRD "Unit tests": buffer edges (30 ok / 29 / overlap / touching); hours (06:00 start, 22:00 end, 22:30 end, 05:30 start, 30 min at 06:30); dated offsets (`+05:30` ok, `+05:45` off-grid, `-05:00` vs `-04:00` same instant, non-zero seconds); slot generation on a normal day, 2026-11-01, 2027-03-14 with correct UTC instants; reason precedence; `start == now` create ok / cancel rejected; duration off-grid, <30, >8h

**Gate:** unit tests green (run without a database).
**Result (2026-10-01):** passed. `pytest tests/test_rules.py` with no database env: `50 passed`. Ruff clean.

## Step 3 — Seed

- [x] `python seed.py > data/seed.json` (unmodified script); sanity-check: 3,000 bookings, 5 ships, both `-05:00` and `-06:00` present
- [x] `scripts/load_seed.py`: advisory lock → no-op if `bookings` has rows → validate every row with `rules.py` (hours, grid, duration; exempt from R6) → insert ships with ids + all bookings in one transaction; any violation fails the whole load loudly
- [x] `SEED_FILE` override
- [x] Wire into entrypoint and `init_db --reset`
- [x] Tests (small fixture, not the seed file): loads; second run inserts nothing; a bad row aborts with nothing committed

**Gate:** fresh `docker compose down -v && up` → `SELECT count(*) FROM bookings` = 3000; restart → still 3000.
**Result (2026-10-01):** passed. Fresh volume: `loaded 3000 bookings from /app/data/seed.json`, 5 ships; after restart: `nothing loaded`, still 3000. `init_db --reset` reloads 3000. Suite: `90 passed`. Seed spans 2025-10-01 → 2026-06-05, both offsets present.

## Step 4 — Booking API

- [x] Fixed-clock test fixture (moved from step 1; the clock dependency is born here)
- [x] `app/schemas.py`: camelCase alias generator; `BookingCreate` (`extra='forbid'`, trimmed 1–100 name, aware timestamps, zero seconds); `BookingOut` (Central-offset timestamps); availability models; error envelope
- [x] Error handling in `main.py`: domain errors → envelope; `RequestValidationError` → 422 `validation_error`; `HTTPException` → envelope (`not_found`); unhandled → 500 `internal_error`, no trace; unknown `/api/*` → 404 envelope
- [x] Clock dependency (one read per operation; overridable in tests)
- [x] `GET /api/ships`
- [x] `services/availability.py` + `GET /api/ships/{id}/availability` → slots, `lastStart`, `serverNow`, `timezone`; 404 ship; 422 bad date/duration
- [x] `services/bookings.py` create: rules → pre-check with the same `tsrange` expression → (hook, A6) → insert; `23P01` → 409 `booking_conflict`, other integrity errors → 500
- [x] `POST /api/bookings` → 201 / 404 / 409 / 422
- [x] Integration tests: create 201 + same slot 409; passed start → 409 `in_the_past`; **coordinated race** (exactly one 201, one 409); request after an exclusion failure succeeds; availability marks `past`/`booked`/`buffer` and changes after a booking; naive timestamp 422; unknown field 422; unknown ship 404; 101-char name 422; every error (incl. validation and a forced unhandled exception) in the envelope

**Gate:** integration tests green, including the race test.
**Result (2026-10-01):** passed. `134 passed`, including the coordinated race (both pre-checks saw a free slot; exactly one 201 and one 409 `booking_conflict`; one row). Race test repeated 5× with no flake.

## Step 5 — Read and cancel API

- [x] `GET /api/bookings` (`from`, `to` required, inclusive Central dates, `from ≤ to`, ≤ 31 days, optional `shipId` → 404 if unknown, `includeCancelled`); ordered ship, start, id
- [x] `GET /api/bookings/nearest-dates` → `{ previous, next }` (A3)
- [x] `DELETE /api/bookings/{id}`: single atomic `UPDATE … RETURNING`; on no row, look up → 404 / `already_cancelled` / `already_started`
- [x] Integration tests: cancel 200 and the slot is bookable again; in-progress → 409 `already_started`; two simultaneous cancels → one 200, one 409; `includeCancelled` on/off; `from > to` 422; >31 days 422; ordering; `nearest-dates` both directions, nulls, and with the flag

**Gate:** full backend suite green; ruff clean.
**Result (2026-10-01):** passed. Full suite in the `test` service: `162 passed`; ruff clean. Live smoke against the seeded app: availability, bookings list and `nearest-dates` (`previous: 2026-06-05, next: null`) return the documented shapes.

## Step 6 — Frontend shell

- [x] Dockerfile node build stage (moved from step 1)
- [x] Vite + React + TS, React Router, TanStack Query, CSS modules, ESLint + Prettier, `package-lock.json`
- [x] Vite dev proxy `/api` → `:8000`
- [x] `src/api/`: typed client (envelope parsing; non-JSON → "Something went wrong"; no-response → distinct error type), query hooks, mutations with `retry: false`
- [x] `src/lib/time.ts`: the only place that formats time — always `timeZone: 'America/Chicago'`, "CT" label, local-time hint (with weekday when the date differs), Central "today" from `serverNow`, plain `YYYY-MM-DD` date arithmetic (no `Date`/`toISOString` for dates)
- [x] Layout: top nav, shared-demo banner, `aria-live` message region, shared loading / error+Retry / empty components
- [x] Routes `/` and `/fleet` (stubs showing ships and a Central time)
- [x] FastAPI: serve `/app/static`, fall back to `index.html` for non-API, non-file paths; Dockerfile node stage does the real build

**Gate:** `docker compose up --build` → `/` and `/fleet` load, refresh on `/fleet` works, a time renders in CT; lint clean.
**Result (2026-10-01):** passed. `/` and `/fleet` both return the app from the container (refresh on `/fleet` works), unknown `/api/*` stays a JSON 404, times render in CT. `npm run lint` and `tsc` clean. Backend suite now `169 passed` (adds frontend-serving and `/api/time` tests).

## Step 7 — Charter page

- [x] Controls: ship select ("No ships available" on empty), date picker (min = Central today from `serverNow`), duration select 30 min–8 h
- [x] `SlotGrid`: one button per slot; disabled ones show "Booked" / "Refuel" / "Past" as visible text; caption from `lastStart`
- [x] Booking panel: selected range, pilot name, Book button (disabled until slot + name, and in flight → "Booking…")
- [x] Sends the slot's exact `start`/`end` strings
- [x] Success banner + refresh; 409 → message + refresh, name kept; no-response → "We couldn't confirm…" + refresh
- [x] Selection rules: cleared on ship/date/duration change and when missing/unavailable after a refresh; name kept
- [x] Invalidation by prefix `['availability', shipId, date]`, plus bookings and `nearest-dates`
- [x] Refetch on focus/reconnect; 60 s interval for today's availability while visible; day rolls over from `serverNow`

**Gate:** in the browser: book a slot, see it and its buffer greyed; force a 409 (book the same slot from a second tab) and an offline failure; lint clean.
**Result (2026-10-01):** passed in Chrome against the seeded app. Booked 10:00 AM–12:00 PM: success banner, slots turn Booked with Refuel either side. Changing duration cleared the selection and kept the pilot name. A competing booking made through the API produced the 409 message "That time overlaps another booking.", the grid refreshed, the name stayed. A failed POST produced the "couldn't confirm" message and a refresh.

## Step 8 — Dashboard

- [x] Header: date picker, prev/next, Today, "Show cancelled"
- [x] `FleetTimeline`: 06:00–22:00 axis, row per ship, blocks positioned by Central time, hatched 30-min buffer clipped at 22:00, active bookings only
- [x] Grouped list by ship below (cancelled shown only here, marked); list-only on narrow screens
- [x] Empty state with previous/next "day with bookings" links, disabled when null
- [x] `BookingDetails`: ship, pilot, times, status; focus moves in and returns on close; Cancel (confirm, disabled in flight) only for upcoming active bookings, judged against `serverNow`
- [x] Cancel success → invalidate bookings, `nearest-dates`, that ship/date's availability; cancel 409 → message + refresh list and panel

**Gate:** in the browser: navigate to a seeded day (via "Previous day with bookings"), book today, cancel it from the dashboard, toggle cancelled, rebook the freed slot; lint clean.
**Result (2026-10-01):** passed in Chrome. Empty today → "Next day with bookings" jumps to the booked day; details open from both timeline and list; cancel asks for confirmation, removes the booking, shows the notice; "Show cancelled" lists it as Cancelled while the timeline stays active-only; a booking cancelled behind the UI's back gives the 409 message and the panel updates to Cancelled with no Cancel button.

## Step 9 — Time-zone and checklist pass

- [x] Emulate `Asia/Tokyo` and `America/Los_Angeles`: dates/times unchanged, hint shows local time and the date when it differs, default date is Central today
- [x] Walk the full manual checklist from PRD "Testing → Frontend" (flows incl. 409 and network failure, selection behaviour, visible reasons + keyboard, focus + live region, narrow screen, time zones) and record pass/fail per line here

**Gate:** every checklist line passes or has a fix committed.
**Result (2026-10-01):** passed, with one item not verified. Scripted Chrome under `America/Chicago`, `Asia/Tokyo` and `America/Los_Angeles`, run at about 10:30 PM Central (Tokyo already on Oct 2):

- [x] Flows end to end, including a 409 and a simulated network failure (steps 7 and 8).
- [x] Changing ship, date or duration clears the selection and keeps the pilot name.
- [x] Unavailable reasons are text on the button. Keyboard only: slot chosen with Enter, form submitted with Enter, booking cancelled with Enter/Enter, dialog closed with Escape.
- [x] Details panel: focus moves in, Tab stays inside, focus returns to the booking that opened it (timeline block and list entry). Fixed along the way: focus is now restored explicitly (Safari doesn't focus buttons on click) and stays on the confirm step.
- [ ] **Not verified:** announcement by an actual screen reader. The messages are in `role="status"` / `aria-live="polite"` regions that exist before the text appears, but nobody has listened to VoiceOver read them.
- [x] At 420 px wide the timeline is hidden, the grouped list shows, no horizontal scroll; cancelled bookings appear only in the list.
- [x] Tokyo and Los Angeles: default date is Central today (`2026-10-01`, while the Tokyo browser's own date was `2026-10-02`); a picked date doesn't shift; slot times, list times and timeline positions are identical in all three zones; a 9:00 PM booking is stored as `2026-10-03T21:00:00-05:00` from every zone; hint reads "Sat 9:00 PM CT (Sun 11:00 AM your time)" in Tokyo and "9:00 PM CT (7:00 PM your time)" in Los Angeles.

## Step 10 — README

- [x] Move the brief to `BRIEF.md` (A1)
- [x] README: one-command run, tests, reset, local dev; architecture summary; business rules; decision log; known limitations (lock-wait boundary, schema changes need a reset, shared demo); what I'd do next

**Gate:** fresh clone in a scratch directory → `docker compose up --build` works with no other steps; test command green.
**Result (2026-10-01):** passed. Copied only the files a clone would contain to a scratch directory: `docker compose up --build` → health 200, `/fleet` 200, `loaded 3000 bookings`; test service `169 passed`.

## Step 11 — Railway (confirm first, A10)

- [x] `railway.toml`: Dockerfile build, health check path `/api/health`
- [ ] Push to a public GitHub repo
- [ ] Project + Postgres + app service from the repo; `DATABASE_URL` as a variable reference; public domain
- [ ] Deploy log shows `CREATE EXTENSION btree_gist` succeeded and the seed loaded
- [ ] Record every setting made through the CLI/MCP in the PRD or `railway.toml`; add the URL to the README

**Gate:** the live URL books and cancels; a redeploy keeps the data and doesn't re-seed.
**Result:**

---

## Deviations

- **Step 1.** Node build stage deferred to step 6 (no frontend to build yet) and the fixed-clock fixture to step 4, instead of placeholders.
- **Step 1.** `PORT` is read by `entrypoint.sh`, not `config.py`; `SEED_FILE` joins `config.py` in step 3.
- **Step 1.** Compose publishes Postgres on host port **5433** (5432 is taken by a local Postgres on this machine). Containers still use 5432.
- **Step 6.** New endpoint `GET /api/time` → `{ serverNow, timezone }`. The PRD takes "today" from the latest `serverNow`, but only availability returned one and the dashboard never calls availability. Both pages now read the clock from `/api/time` (refetched every 60 s and after every booking or cancel). Added to the PRD's API table.
- **Step 6.** Fonts are bundled from `@fontsource` packages (Barlow Condensed, IBM Plex Sans, IBM Plex Mono): three extra frontend dependencies, no network request at runtime.
- **Step 8.** The details panel is a native modal `<dialog>` rather than a side panel: the browser provides the focus trap and Escape.
- **Step 9 (A8).** Chrome DevTools MCP has no timezone override, so the pass used a throwaway Puppeteer script (`page.emulateTimezone`) driving the installed Chrome. The script lives outside the repo.
- **Step 4 (A6).** No hook was added to the service for the race test. The pre-check is its own function, `find_conflicts`; the test wraps it to wait at a barrier after it returns. Production code has no test-only seam.
- **Step 4.** Rule violations that depend only on the request (`not_on_grid`, `invalid_duration`, `outside_operating_hours`) return 422; state-dependent ones return 409, as the PRD says. `/api/health` failures use the envelope too, with code `database_unavailable` (503).
- **Step 4.** Timestamps must be ISO strings: a JSON number is rejected (Pydantic would otherwise read it as a Unix timestamp with no offset to check).
- **Step 2.** Dev dependency is `httpx2`, not `httpx`: Starlette's test client now deprecates `httpx`.
- **Step 1.** Image pins resolved and written into the PRD: `python:3.12.15-slim-bookworm`, `postgres:16.15-bookworm`, `node:22.23.3-bookworm-slim`; uv `0.12.13`.
