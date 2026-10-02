"""Unit tests for rules.py. No database: run with `pytest tests/test_rules.py`."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app import rules
from app.rules import Interval, RuleViolation

DAY = date(2026, 10, 2)  # a Friday in CDT (-05:00)
EARLY = datetime(2026, 10, 1, 12, 0, tzinfo=rules.TZ)  # a "now" before every DAY slot


def ct(hhmm: str, day: date = DAY) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=rules.TZ)


def iv(start: str, end: str) -> Interval:
    return Interval(ct(start), ct(end))


def violation(start: datetime, end: datetime, now: datetime = EARLY) -> str | None:
    try:
        rules.check_new_booking(start, end, now)
    except RuleViolation as exc:
        return exc.code
    return None


class TestBuffer:
    BOOKING = iv("08:00", "10:00")

    def test_gap_of_exactly_30_minutes_allowed(self):
        assert not rules.conflicts(iv("10:30", "11:30"), self.BOOKING)
        assert not rules.conflicts(iv("07:00", "07:30"), self.BOOKING)

    def test_gap_of_29_minutes_rejected(self):
        after = Interval(ct("10:00") + timedelta(minutes=29), ct("11:30"))
        before = Interval(ct("07:00"), ct("08:00") - timedelta(minutes=29))
        assert rules.conflicts(after, self.BOOKING)
        assert rules.conflicts(before, self.BOOKING)

    def test_overlap_rejected(self):
        for candidate in [iv("09:00", "11:00"), iv("07:00", "08:30"), iv("08:30", "09:00")]:
            assert rules.conflicts(candidate, self.BOOKING)
            assert rules.overlaps(candidate, self.BOOKING)

    def test_touching_end_to_start_rejected(self):
        assert rules.conflicts(iv("10:00", "11:00"), self.BOOKING)
        assert rules.conflicts(iv("07:00", "08:00"), self.BOOKING)
        # Half-open intervals: touching is a buffer problem, not an overlap.
        assert not rules.overlaps(iv("10:00", "11:00"), self.BOOKING)

    def test_conflict_is_symmetric(self):
        assert rules.conflicts(self.BOOKING, iv("10:00", "11:00"))
        assert not rules.conflicts(self.BOOKING, iv("10:30", "11:30"))


class TestOperatingHours:
    def test_start_at_opening_accepted(self):
        assert violation(ct("06:00"), ct("07:00")) is None

    def test_end_at_closing_accepted(self):
        assert violation(ct("21:00"), ct("22:00")) is None

    def test_8_hours_ending_at_closing_accepted(self):
        assert violation(ct("14:00"), ct("22:00")) is None

    def test_end_after_closing_rejected(self):
        assert violation(ct("21:30"), ct("22:30")) == "outside_operating_hours"

    def test_start_before_opening_rejected(self):
        assert violation(ct("05:30"), ct("06:30")) == "outside_operating_hours"

    def test_30_minutes_at_0630_accepted(self):
        assert violation(ct("06:30"), ct("07:00")) is None

    def test_crossing_midnight_rejected(self):
        next_day = DAY + timedelta(days=1)
        assert violation(ct("21:00"), ct("05:00", next_day)) == "outside_operating_hours"


class TestOffsets:
    """Any UTC offset is accepted and converted to Central. 2026-10-02 is CDT (-05:00)."""

    def test_plus_0530_that_lands_on_6am_central_accepted(self):
        start = datetime.fromisoformat("2026-10-02T16:30:00+05:30")
        end = datetime.fromisoformat("2026-10-02T17:30:00+05:30")
        assert rules.to_central(start) == ct("06:00")
        assert violation(start, end) is None

    def test_plus_0545_that_lands_on_0615_central_rejected(self):
        start = datetime.fromisoformat("2026-10-02T17:00:00+05:45")
        end = datetime.fromisoformat("2026-10-02T18:00:00+05:45")
        assert rules.to_central(start).strftime("%H:%M") == "06:15"
        assert violation(start, end) == "not_on_grid"

    def test_same_instant_in_two_offsets_treated_identically(self):
        central = (
            datetime.fromisoformat("2026-10-02T05:30:00-05:00"),
            datetime.fromisoformat("2026-10-02T06:30:00-05:00"),
        )
        eastern = (
            datetime.fromisoformat("2026-10-02T06:30:00-04:00"),
            datetime.fromisoformat("2026-10-02T07:30:00-04:00"),
        )
        assert central == eastern
        # 5:30 AM Central, however it is written.
        assert violation(*central) == violation(*eastern) == "outside_operating_hours"

    def test_same_offsets_mean_a_different_hour_in_winter(self):
        # 2026-12-02 is CST (-06:00): 16:30+05:30 is now 5:00 AM Central.
        start = datetime.fromisoformat("2026-12-02T16:30:00+05:30")
        end = datetime.fromisoformat("2026-12-02T17:30:00+05:30")
        assert violation(start, end) == "outside_operating_hours"

    def test_non_zero_seconds_rejected(self):
        start = datetime.fromisoformat("2026-10-02T06:00:30-05:00")
        end = datetime.fromisoformat("2026-10-02T07:00:30-05:00")
        assert violation(start, end) == "not_on_grid"

    def test_fractional_seconds_rejected(self):
        start = datetime.fromisoformat("2026-10-02T06:00:00.500-05:00")
        assert violation(start, ct("07:00")) == "not_on_grid"
        assert violation(ct("06:00"), ct("07:00") + timedelta(microseconds=1)) == "not_on_grid"

    def test_naive_datetime_is_a_programming_error(self):
        with pytest.raises(ValueError):
            rules.check_interval(datetime(2026, 10, 2, 6, 0), ct("07:00"))


class TestDuration:
    def test_off_grid_duration_rejected(self):
        assert violation(ct("06:00"), ct("06:45")) == "not_on_grid"
        with pytest.raises(RuleViolation) as exc:
            rules.check_duration(timedelta(minutes=45))
        assert exc.value.code == "invalid_duration"

    def test_under_30_minutes_rejected(self):
        for minutes in (0, 15, -30):
            with pytest.raises(RuleViolation):
                rules.check_duration(timedelta(minutes=minutes))

    def test_end_not_after_start_rejected(self):
        assert violation(ct("07:00"), ct("07:00")) == "invalid_duration"
        assert violation(ct("08:00"), ct("07:00")) == "invalid_duration"

    def test_over_8_hours_rejected(self):
        assert violation(ct("06:00"), ct("14:30")) == "invalid_duration"

    def test_30_minutes_and_8_hours_accepted(self):
        assert violation(ct("06:00"), ct("06:30")) is None
        assert violation(ct("06:00"), ct("14:00")) is None


class TestNow:
    def test_creating_with_start_equal_to_now_allowed(self):
        assert violation(ct("09:00"), ct("10:00"), now=ct("09:00")) is None

    def test_creating_after_start_rejected(self):
        now = ct("09:00") + timedelta(seconds=1)
        assert violation(ct("09:00"), ct("10:00"), now=now) == "in_the_past"

    def test_now_in_another_offset_is_the_same_instant(self):
        now = ct("09:00").astimezone(UTC)
        assert violation(ct("09:00"), ct("10:00"), now=now) is None

    def test_cancelling_with_start_equal_to_now_rejected(self):
        assert not rules.can_cancel(ct("09:00"), now=ct("09:00"))

    def test_cancelling_before_start_allowed(self):
        assert rules.can_cancel(ct("09:00"), now=ct("09:00") - timedelta(seconds=1))

    def test_cancelling_in_progress_rejected(self):
        assert not rules.can_cancel(ct("09:00"), now=ct("09:30"))

    def test_seed_history_is_exempt_from_the_past_rule(self):
        rules.check_interval(ct("09:00"), ct("10:00"))  # no `now`, no error


class TestSlots:
    @pytest.mark.parametrize(
        ("day", "utc_hour", "offset_hours"),
        [
            (date(2026, 10, 2), 11, -5),  # normal CDT day
            (date(2026, 10, 31), 11, -5),  # last CDT day
            (date(2026, 11, 1), 12, -6),  # DST ends at 2:00 AM this morning
            (date(2027, 3, 13), 12, -6),  # last CST day
            (date(2027, 3, 14), 11, -5),  # DST starts at 2:00 AM this morning
        ],
    )
    def test_6am_central_maps_to_the_right_utc_instant(self, day, utc_hour, offset_hours):
        slots = rules.day_slots(day, timedelta(minutes=30))
        first, last = slots[0], slots[-1]

        assert first.start == datetime(day.year, day.month, day.day, utc_hour, tzinfo=UTC)
        assert first.start.utcoffset() == timedelta(hours=offset_hours)
        assert first.start.isoformat().endswith(f"T06:00:00-0{-offset_hours}:00")
        # Every operating day is exactly 16 hours: 32 half-hour slots, closing at 10 PM.
        assert len(slots) == 32
        assert last.end.astimezone(UTC) - first.start.astimezone(UTC) == timedelta(hours=16)
        assert last.end.isoformat().endswith(f"T22:00:00-0{-offset_hours}:00")

    @pytest.mark.parametrize(
        ("minutes", "count", "last"),
        [(30, 32, "21:30"), (60, 31, "21:00"), (240, 25, "18:00"), (480, 17, "14:00")],
    )
    def test_slots_stop_at_the_last_start_that_fits(self, minutes, count, last):
        duration = timedelta(minutes=minutes)
        slots = rules.day_slots(DAY, duration)

        assert len(slots) == count
        assert slots[0] == Interval(ct("06:00"), ct("06:00") + duration)
        assert slots[-1].start == ct(last) == rules.last_start(DAY, duration)
        assert slots[-1].end == ct("22:00")
        assert all(b.start - a.start == rules.GRID for a, b in zip(slots, slots[1:], strict=False))

    def test_every_slot_is_a_valid_booking(self):
        for minutes in range(30, 481, 30):
            for slot in rules.day_slots(DAY, timedelta(minutes=minutes)):
                rules.check_interval(*slot)

    def test_invalid_duration_rejected(self):
        for minutes in (0, 45, 510):
            with pytest.raises(RuleViolation):
                rules.day_slots(DAY, timedelta(minutes=minutes))

    def test_day_bounds_follow_central_midnight_across_dst(self):
        start, end = rules.day_bounds(date(2026, 11, 1))
        assert start == datetime(2026, 11, 1, 5, tzinfo=UTC)
        assert end == datetime(2026, 11, 2, 6, tzinfo=UTC)  # a 25-hour day


class TestSlotReason:
    BOOKINGS = [iv("10:00", "12:00")]

    def reason(self, start: str, end: str, now: datetime = EARLY) -> str | None:
        return rules.slot_reason(iv(start, end), self.BOOKINGS, now)

    def test_free_slot(self):
        assert self.reason("06:00", "07:00") is None
        assert self.reason("08:30", "09:30") is None  # ends exactly 30 minutes before
        assert self.reason("12:30", "13:30") is None  # starts exactly 30 minutes after

    def test_slot_inside_a_booking_is_booked(self):
        assert self.reason("10:00", "11:00") == "booked"
        assert self.reason("11:30", "12:30") == "booked"

    def test_slot_starting_free_but_running_into_a_booking_is_booked(self):
        assert self.reason("09:00", "10:30") == "booked"
        assert self.reason("08:00", "13:00") == "booked"

    def test_slot_only_touching_the_margin_is_buffer(self):
        assert self.reason("12:00", "13:00") == "buffer"  # starts as the booking ends
        assert self.reason("09:00", "10:00") == "buffer"  # ends as the booking starts
        assert self.reason("08:00", "09:30") is None
        assert self.reason("08:30", "10:00") == "buffer"

    def test_past_wins_over_buffer_and_booked(self):
        now = ct("12:15")
        assert self.reason("12:00", "13:00", now) == "past"  # also in the buffer
        assert self.reason("11:00", "12:00", now) == "past"  # also booked
        assert self.reason("06:00", "07:00", now) == "past"

    def test_slot_starting_exactly_now_is_not_past(self):
        assert self.reason("13:00", "14:00", now=ct("13:00")) is None

    def test_future_date_has_no_past_slots(self):
        slots = rules.day_slots(DAY, timedelta(hours=1))
        assert all(rules.slot_reason(s, [], EARLY) is None for s in slots)
