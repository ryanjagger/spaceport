from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.clock import NowDep
from app.db import SessionDep
from app.schemas import BookingCreate, BookingOut, NearestDatesOut
from app.services import bookings

router = APIRouter()

MAX_RANGE_DAYS = 31


@router.get("/bookings", response_model=list[BookingOut])
def list_bookings(
    session: SessionDep,
    first_day: Annotated[date, Query(alias="from")],
    last_day: Annotated[date, Query(alias="to")],
    ship_id: Annotated[int | None, Query(alias="shipId")] = None,
    include_cancelled: Annotated[bool, Query(alias="includeCancelled")] = False,
):
    if first_day > last_day:
        raise HTTPException(422, "from must not be after to")
    if (last_day - first_day).days >= MAX_RANGE_DAYS:
        raise HTTPException(422, f"from and to may span at most {MAX_RANGE_DAYS} dates")
    return bookings.list_bookings(session, first_day, last_day, ship_id, include_cancelled)


@router.get("/bookings/nearest-dates", response_model=NearestDatesOut)
def nearest_dates(
    session: SessionDep,
    day: Annotated[date, Query(alias="date")],
    include_cancelled: Annotated[bool, Query(alias="includeCancelled")] = False,
):
    previous, following = bookings.nearest_dates(session, day, include_cancelled)
    return NearestDatesOut(previous=previous, next=following)


@router.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(data: BookingCreate, session: SessionDep, now: NowDep):
    return bookings.create_booking(session, data, now)


@router.delete("/bookings/{booking_id}", response_model=BookingOut)
def cancel_booking(booking_id: int, session: SessionDep, now: NowDep):
    return bookings.cancel_booking(session, booking_id, now)
