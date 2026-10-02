from datetime import date, datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import rules
from app.errors import NotFoundError
from app.models import Booking
from app.rules import RuleViolation
from app.schemas import BookingCreate
from app.services.ships import get_ship

EXCLUSION_VIOLATION = "23P01"

# The same expression as the no_overlap_with_buffer constraint in schema.sql.
CONFLICTS_WITH_CANDIDATE = text(
    "tsrange(start_time AT TIME ZONE 'UTC', "
    "(end_time AT TIME ZONE 'UTC') + interval '30 minutes', '[)') "
    "&& tsrange(CAST(:start AS timestamptz) AT TIME ZONE 'UTC', "
    "(CAST(:end AS timestamptz) AT TIME ZONE 'UTC') + interval '30 minutes', '[)')"
)


def find_conflicts(session: Session, ship_id: int, start: datetime, end: datetime) -> list[Booking]:
    """Active bookings on the ship that overlap the candidate or its refuel buffer."""
    return list(
        session.scalars(
            select(Booking)
            .where(Booking.ship_id == ship_id, Booking.status == "active")
            .where(CONFLICTS_WITH_CANDIDATE.bindparams(start=start, end=end))
        )
    )


def create_booking(session: Session, data: BookingCreate, now: datetime) -> Booking:
    rules.check_new_booking(data.start_time, data.end_time, now)
    get_ship(session, data.ship_id)

    # A pre-check only so the message can say what is in the way. It cannot stop
    # two simultaneous requests: the exclusion constraint below does that.
    candidate = rules.Interval(data.start_time, data.end_time)
    conflicts = find_conflicts(session, data.ship_id, *candidate)
    if conflicts:
        if any(
            rules.overlaps(candidate, rules.Interval(b.start_time, b.end_time)) for b in conflicts
        ):
            raise RuleViolation("booking_conflict", "That time overlaps another booking.")
        raise RuleViolation(
            "booking_conflict",
            "That time is within the 30-minute refuel buffer of another booking.",
        )

    booking = Booking(
        ship_id=data.ship_id,
        pilot_name=data.pilot_name,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    session.add(booking)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # Someone else's insert won the race. Any other integrity error is a bug: let it be a 500.
        if getattr(exc.orig, "sqlstate", None) == EXCLUSION_VIOLATION:
            raise RuleViolation("booking_conflict", "That time was just booked.") from exc
        raise
    session.refresh(booking)
    return booking


def list_bookings(
    session: Session,
    first_day: date,
    last_day: date,
    ship_id: int | None = None,
    include_cancelled: bool = False,
) -> list[Booking]:
    """Bookings starting on the Central dates first_day..last_day, both inclusive."""
    if ship_id is not None:
        get_ship(session, ship_id)

    query = select(Booking).where(
        Booking.start_time >= rules.day_bounds(first_day).start,
        Booking.start_time < rules.day_bounds(last_day).end,
    )
    if ship_id is not None:
        query = query.where(Booking.ship_id == ship_id)
    if not include_cancelled:
        query = query.where(Booking.status == "active")
    return list(session.scalars(query.order_by(Booking.ship_id, Booking.start_time, Booking.id)))


def nearest_dates(
    session: Session, day: date, include_cancelled: bool = False
) -> tuple[date | None, date | None]:
    """The closest Central dates before and after `day` that have bookings, fleet-wide."""
    day_start, day_end = rules.day_bounds(day)
    visible = [] if include_cancelled else [Booking.status == "active"]

    previous = session.scalar(
        select(func.max(Booking.start_time)).where(Booking.start_time < day_start, *visible)
    )
    following = session.scalar(
        select(func.min(Booking.start_time)).where(Booking.start_time >= day_end, *visible)
    )
    return (
        rules.to_central(previous).date() if previous else None,
        rules.to_central(following).date() if following else None,
    )


def cancel_booking(session: Session, booking_id: int, now: datetime) -> Booking:
    # One atomic statement: of two simultaneous cancels, only one finds an active row.
    cancelled = session.scalars(
        update(Booking)
        .where(Booking.id == booking_id, Booking.status == "active", Booking.start_time > now)
        .values(status="cancelled", cancelled_at=func.now())
        .returning(Booking)
    ).one_or_none()
    session.commit()
    if cancelled is not None:
        return cancelled

    # Nothing was updated; look the booking up only to explain why.
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise NotFoundError(f"Booking {booking_id} does not exist.")
    if booking.status == "cancelled":
        raise RuleViolation("already_cancelled", "This booking has already been cancelled.")
    raise RuleViolation(
        "already_started", "This booking has already started and can no longer be cancelled."
    )
