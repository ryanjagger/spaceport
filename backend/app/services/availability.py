from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rules
from app.models import Booking
from app.schemas import AvailabilityOut, SlotOut
from app.services.ships import get_ship


def get_availability(
    session: Session, ship_id: int, day: date, duration_minutes: int, now: datetime
) -> AvailabilityOut:
    get_ship(session, ship_id)
    duration = rules.duration_of(duration_minutes)
    slots = rules.day_slots(day, duration)

    # Only this Central day's bookings: a booking and its buffer end by 10:30 PM,
    # so no other day can affect these slots.
    day_start, day_end = rules.day_bounds(day)
    bookings = session.scalars(
        select(Booking).where(
            Booking.ship_id == ship_id,
            Booking.status == "active",
            Booking.start_time >= day_start,
            Booking.start_time < day_end,
        )
    )
    booked = [rules.Interval(b.start_time, b.end_time) for b in bookings]

    slots_out = []
    for slot in slots:
        reason = rules.slot_reason(slot, booked, now)
        slots_out.append(
            SlotOut(start=slot.start, end=slot.end, available=reason is None, reason=reason)
        )

    return AvailabilityOut(
        ship_id=ship_id,
        date=day,
        timezone=rules.TZ.key,
        server_now=now,
        duration_minutes=duration_minutes,
        last_start=rules.last_start(day, duration),
        slots=slots_out,
    )
