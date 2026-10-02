from typing import Annotated

from fastapi import APIRouter, Query

from app.clock import NowDep
from app.db import SessionDep
from app.schemas import ApiDate, AvailabilityOut, ShipId, ShipOut
from app.services import availability, ships

router = APIRouter()


@router.get("/ships", response_model=list[ShipOut])
def list_ships(session: SessionDep):
    return ships.list_ships(session)


@router.get("/ships/{ship_id}/availability", response_model=AvailabilityOut)
def get_availability(
    ship_id: ShipId,
    session: SessionDep,
    now: NowDep,
    day: Annotated[ApiDate, Query(alias="date")],
    duration_minutes: Annotated[int, Query(alias="durationMinutes")] = 60,
):
    return availability.get_availability(session, ship_id, day, duration_minutes, now)
