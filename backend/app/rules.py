"""The scheduling rules as pure functions: no database, no HTTP, no clock.

Every function takes timezone-aware datetimes in any offset and evaluates them in
spaceport time (America/Chicago). Callers read the clock once and pass `now` in.

Intervals are half-open: [start, end).
"""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
OPENING = time(6, 0)
CLOSING = time(22, 0)
GRID = timedelta(minutes=30)
MIN_DURATION = timedelta(minutes=30)
MAX_DURATION = timedelta(hours=8)
# schema.sql hard-codes the same 30 minutes; init_db.py refuses to start if they differ.
REFUEL_BUFFER = timedelta(minutes=30)


class Interval(NamedTuple):
    start: datetime
    end: datetime


class RuleViolation(Exception):
    """A booking request that breaks a rule. `code` is the API error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def to_central(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("naive datetime: every timestamp must carry an offset")
    return moment.astimezone(TZ)


def opening_time(day: date) -> datetime:
    return datetime.combine(day, OPENING, tzinfo=TZ)


def closing_time(day: date) -> datetime:
    return datetime.combine(day, CLOSING, tzinfo=TZ)


def day_bounds(day: date) -> Interval:
    """The Central calendar day as an interval, midnight to midnight."""
    return Interval(
        datetime.combine(day, time.min, tzinfo=TZ),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=TZ),
    )


def _on_grid(moment: datetime) -> bool:
    return moment.minute in (0, 30) and moment.second == 0 and moment.microsecond == 0


def _invalid_duration() -> RuleViolation:
    return RuleViolation(
        "invalid_duration", "A charter lasts 30 minutes to 8 hours, in 30-minute steps."
    )


def check_duration(duration: timedelta) -> None:
    """R5: 30 minutes to 8 hours, in 30-minute steps."""
    if not MIN_DURATION <= duration <= MAX_DURATION or duration % GRID:
        raise _invalid_duration()


def duration_of(minutes: int) -> timedelta:
    """R5 from a minute count. Checked as an int first: timedelta overflows on huge values."""
    if not 0 < minutes <= MAX_DURATION // timedelta(minutes=1):
        raise _invalid_duration()
    duration = timedelta(minutes=minutes)
    check_duration(duration)
    return duration


def check_interval(start: datetime, end: datetime) -> None:
    """R3, R4 and R5: the rules that depend only on the booking itself.

    Seed data is checked with this (history is exempt from the no-past rule).
    """
    start, end = to_central(start), to_central(end)

    if end <= start:
        raise RuleViolation("invalid_duration", "A charter must end after it starts.")
    if not _on_grid(start) or not _on_grid(end):
        raise RuleViolation(
            "not_on_grid", "Charters start and end on the hour or half hour, Central time."
        )
    # Subtract in UTC: Python subtracts two datetimes in the same zone by wall clock.
    check_duration(end.astimezone(UTC) - start.astimezone(UTC))
    # Comparing against the start's own day also rejects a booking that crosses midnight.
    if start < opening_time(start.date()) or end > closing_time(start.date()):
        raise RuleViolation(
            "outside_operating_hours",
            "Charters must fall between 6:00 AM and 10:00 PM Central on a single day.",
        )


def check_new_booking(start: datetime, end: datetime, now: datetime) -> None:
    """Everything a new booking must satisfy on its own. R6: start == now is allowed."""
    check_interval(start, end)
    if start < now:
        raise RuleViolation("in_the_past", "That start time has already passed.")


def overlaps(a: Interval, b: Interval) -> bool:
    """R1: the two bookings share an instant."""
    return a.start < b.end and b.start < a.end


def conflicts(a: Interval, b: Interval) -> bool:
    """R1 + R2 as one test: the bookings overlap or sit less than 30 minutes apart."""
    return a.start < b.end + REFUEL_BUFFER and b.start < a.end + REFUEL_BUFFER


def can_cancel(start: datetime, now: datetime) -> bool:
    """R8: only before the booking starts. start == now is already in progress."""
    return start > now


def last_start(day: date, duration: timedelta) -> datetime:
    return closing_time(day) - duration


def day_slots(day: date, duration: timedelta) -> list[Interval]:
    """Every start on the 30-minute grid whose end fits by closing time.

    Wall-clock arithmetic is safe here: DST switches at 2:00 AM, outside operating hours.
    """
    check_duration(duration)
    slots = []
    start = opening_time(day)
    while start <= last_start(day, duration):
        slots.append(Interval(start, start + duration))
        start += GRID
    return slots


def slot_reason(slot: Interval, bookings: Iterable[Interval], now: datetime) -> str | None:
    """Why a slot can't be booked, or None if it can. First match wins: past, booked, buffer."""
    if slot.start < now:
        return "past"
    bookings = list(bookings)
    if any(overlaps(slot, b) for b in bookings):
        return "booked"
    if any(conflicts(slot, b) for b in bookings):
        return "buffer"
    return None
