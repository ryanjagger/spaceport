"""API models. JSON is camelCase; Python stays snake_case."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    StringConstraints,
)
from pydantic.alias_generators import to_camel

from app import rules


def _iso_string_only(value: Any) -> Any:
    # Pydantic would otherwise read a number as a Unix timestamp, which has no offset to check.
    if not isinstance(value, str):
        raise ValueError("Input should be an ISO 8601 string with a UTC offset")
    return value


# Responses always show spaceport time, whatever offset the instant was stored or sent in.
CentralDatetime = Annotated[
    datetime, PlainSerializer(lambda dt: rules.to_central(dt).isoformat(), return_type=str)
]
# Requests may use any offset, but must have one.
RequestDatetime = Annotated[AwareDatetime, BeforeValidator(_iso_string_only)]
PilotName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ShipOut(ApiModel):
    id: int
    name: str


class BookingCreate(ApiModel):
    model_config = ConfigDict(extra="forbid")

    ship_id: int
    pilot_name: PilotName
    start_time: RequestDatetime
    end_time: RequestDatetime


class BookingOut(ApiModel):
    id: int
    ship_id: int
    pilot_name: str
    start_time: CentralDatetime
    end_time: CentralDatetime
    status: Literal["active", "cancelled"]
    created_at: CentralDatetime
    cancelled_at: CentralDatetime | None


class SlotOut(ApiModel):
    start: CentralDatetime
    end: CentralDatetime
    available: bool
    reason: Literal["past", "booked", "buffer"] | None


class AvailabilityOut(ApiModel):
    ship_id: int
    date: date
    timezone: str
    server_now: CentralDatetime
    duration_minutes: int
    last_start: CentralDatetime
    slots: list[SlotOut]


class NearestDatesOut(ApiModel):
    previous: date | None
    next: date | None


class ServerTimeOut(ApiModel):
    server_now: CentralDatetime
    timezone: str
