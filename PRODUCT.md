# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Confirmed: design decisions serve the people in the product's own scenario first, not the reviewers of the take-home.

- **Dispatcher.** Books one of the Pacific Spaceport's five charter ships for a pilot. Picks a ship, a date and a duration, sees which start times are open, and books one. Replaces a clipboard, a whiteboard and shouting.
- **Fleet manager.** Looks at a whole day across the fleet, ship by ship, finds a specific booking, and cancels upcoming ones.

Dispatcher and manager are screens, not permission levels. There is no sign-in; anyone can use either screen.

## Product Purpose

A two-screen booking app for the spaceport's charter fleet. It exists so a ship can be booked without breaking the scheduling rules, and so the fleet's day can be read at a glance.

Success means:

- A dispatcher books an available slot and never has to guess why a time is unavailable.
- A double booking or a too-short refuel gap is impossible, even when two people book at the same moment.
- A manager can see every booking for any date, grouped by ship, and free a slot by cancelling.

## Positioning

The backend owns every scheduling rule and Postgres enforces overlap and refuel buffer with one exclusion constraint. The interface never computes availability itself: it shows what the server says, with the reason each time is unavailable, and treats a conflict as "the world moved on" rather than as a user error.

## Operating Context

- Two routes: `/` (Charter a Ship) and `/fleet` (Fleet Manager Dashboard).
- Every date and time is spaceport time (`America/Chicago`), labelled "CT", for every viewer, like an airline departure time. A viewer outside Central also sees their own time as a hint.
- "Today" comes from the server's clock, not the device's.
- Operating day is 6:00 AM to 10:00 PM CT, always 16 hours.
- Several people may book at once; today's availability refetches every 60 seconds and on window focus.
- Seed data is a year of history ending in early June 2026, so the current day starts empty. The dashboard offers "Previous day with bookings" to reach it.
- A shared public demo runs on Railway; anyone with the link can book or cancel.

## Capabilities and Constraints

Capabilities:

- Book: ship, Central date (today or later), duration (30 minutes to 8 hours in 30-minute steps), start time on :00 or :30, free-text pilot name.
- Unavailable start times carry a reason: `booked`, `buffer` (refuel) or `past`.
- Fleet view: one timeline row per ship for a chosen day, plus the same bookings as a list grouped by ship. The 30-minute refuel buffer after each active booking is shown.
- Cancel an active booking that has not started (soft delete). A "Show cancelled" toggle adds cancelled bookings to the list; the timeline shows active bookings only.
- Empty days link to the nearest earlier and later days with bookings.

Rules the interface must reflect, never contradict:

- No overlap on a ship; at least 30 minutes between bookings (exactly 30 is fine).
- Bookings sit entirely within operating hours on one day.
- No bookings in the past.
- Booking and cancel requests are never retried automatically. A 409 is shown with the API's message and the view refreshes; a request with no response is reported as unconfirmed.

Terminology: ship, charter, booking, pilot, slot, refuel buffer, spaceport time / CT, active, cancelled.

Non-goals: authentication and roles, editing or rescheduling (cancel and rebook), multi-day or recurring bookings, notifications.

Fleet (fixed by the brief): USS Wanderer, Nostromo, Serenity, Rocinante, Millennium Falcon.

Carried over from SPACEPORT-PRD.md and BRIEF.md, not reconfirmed in the init interview:

- This is a take-home submission with a 2 to 3 hour target, and every decision must be explainable on a technical call.
- React frontend and Python backend are required by the brief.

## Brand Commitments

- Name: Spaceport Charter System, for the Pacific Spaceport.
- Voice in the brief: plain and lightly wry ("Welcome, dispatcher").
- The current frontend look (palette and typefaces in `frontend/src/styles/global.css`) is **not binding**. It was a first pass and may be replaced.
- No logo or other identity assets exist.

## Evidence on Hand

- `data/seed.json`: five ships and 3,000 seed bookings, generated from the unmodified `seed.py`.
- Live demo: <https://app-production-a9d8.up.railway.app>.
- `BRIEF.md` (original brief), `SPACEPORT-PRD.md` (full design), `PLAN.md` (build log).
- No real customers, testimonials, usage numbers or imagery. Future work must not invent them.

## Product Principles

1. **The server is the authority.** Show what the backend returned; never infer availability, "today" or a timestamp on the client.
2. **Say why.** An unavailable time, a refused booking or a missing Cancel button always comes with its reason in visible text.
3. **One clock.** Every time is spaceport time and says so.
4. **The world moves.** Other people are booking; stale views refresh and conflicts are handled calmly, keeping what the user typed.
5. **Stay small.** Two screens, five ships, no roles. Serve the dispatcher and the manager before adding anything else.

## Accessibility & Inclusion

From the PRD, not reconfirmed in the init interview:

- Unavailable reasons are visible text on the control, not tooltips, so keyboard and touch users see them.
- The booking details panel takes focus when opened and returns it to the booking that opened it.
- Success and error messages are announced through an `aria-live` region.
- On narrow screens the grouped list is the primary fleet view and the timeline is hidden.

No formal standard (such as a WCAG level) has been set.
