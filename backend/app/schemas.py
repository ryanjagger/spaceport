"""API models. JSON is camelCase; Python stays snake_case."""

import unicodedata
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
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


def _in_supported_years(value: datetime) -> datetime:
    # Year 1 or 9999 parses, then overflows when converted to Central time.
    if not MIN_DATE.year <= value.year <= MAX_DATE.year:
        raise ValueError(f"Input should be between {MIN_DATE.year} and {MAX_DATE.year}")
    return value


def _no_control_characters(value: str) -> str:
    # Postgres text cannot hold NUL, and none of the others belong in a name.
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("Input should not contain control characters")
    return value


# Ids are bounded by their column types: Postgres rejects anything larger outright.
ShipId = Annotated[int, Field(ge=-(2**31), le=2**31 - 1)]
BookingId = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]

# Wide enough for any real booking, narrow enough that date arithmetic cannot overflow.
MIN_DATE = date(2000, 1, 1)
MAX_DATE = date(2100, 12, 31)
ApiDate = Annotated[date, Field(ge=MIN_DATE, le=MAX_DATE)]

# Responses always show spaceport time, whatever offset the instant was stored or sent in.
CentralDatetime = Annotated[
    datetime, PlainSerializer(lambda dt: rules.to_central(dt).isoformat(), return_type=str)
]
# Requests may use any offset, but must have one.
RequestDatetime = Annotated[
    AwareDatetime, BeforeValidator(_iso_string_only), AfterValidator(_in_supported_years)
]
PilotName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(_no_control_characters),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ShipOut(ApiModel):
    id: int
    name: str


class BookingCreate(ApiModel):
    model_config = ConfigDict(extra="forbid")

    ship_id: ShipId
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
