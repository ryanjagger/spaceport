"""Ships, availability and booking creation, through the API against real Postgres."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.main import app
from app.services import bookings as bookings_service
from tests.conftest import FixedClock
from tests.helpers import DAY, book, booked, error_code, payload


def slots_by_start(client: TestClient, *, ship_id=1, day=DAY, duration=60) -> dict[str, dict]:
    response = client.get(
        f"/api/ships/{ship_id}/availability", params={"date": day, "durationMinutes": duration}
    )
    assert response.status_code == 200, response.text
    return {slot["start"][11:16]: slot for slot in response.json()["slots"]}


def booking_count(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM bookings")).scalar_one()


class TestShips:
    def test_lists_the_fleet_in_id_order(self, client: TestClient):
        response = client.get("/api/ships")
        assert response.status_code == 200
        assert response.json() == [{"id": 1, "name": "Serenity"}, {"id": 2, "name": "Rocinante"}]

    def test_empty_fleet_is_an_empty_array(self, client: TestClient, db: Engine):
        with db.begin() as conn:
            conn.execute(text("TRUNCATE bookings, ships"))
        assert client.get("/api/ships").json() == []


class TestCreate:
    def test_returns_201_with_the_booking(self, client: TestClient):
        response = book(client, "06:00", "07:00", pilot="  Naomi Nagata  ")

        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "shipId": 1,
            "pilotName": "Naomi Nagata",  # trimmed
            "startTime": "2026-10-02T06:00:00-05:00",
            "endTime": "2026-10-02T07:00:00-05:00",
            "status": "active",
            "createdAt": response.json()["createdAt"],
            "cancelledAt": None,
        }
        assert response.json()["createdAt"].endswith("-05:00")

    def test_same_slot_again_is_a_conflict(self, client: TestClient):
        booked(client, "06:00", "07:00")
        response = book(client, "06:00", "07:00")
        assert response.status_code == 409
        assert error_code(response) == "booking_conflict"
        assert "overlaps" in response.json()["error"]["message"]

    def test_inside_the_refuel_buffer_is_a_conflict(self, client: TestClient):
        booked(client, "08:00", "10:00")
        for start, end in [("10:00", "11:00"), ("07:00", "08:00")]:
            response = book(client, start, end)
            assert response.status_code == 409
            assert error_code(response) == "booking_conflict"
            assert "refuel" in response.json()["error"]["message"]

    def test_exactly_30_minutes_apart_is_allowed(self, client: TestClient):
        booked(client, "08:00", "10:00")
        booked(client, "10:30", "11:30")
        booked(client, "07:00", "07:30")

    def test_other_ship_is_unaffected(self, client: TestClient):
        booked(client, "08:00", "10:00", ship_id=1)
        booked(client, "08:00", "10:00", ship_id=2)

    def test_start_that_has_passed_is_409_in_the_past(self, client: TestClient, clock: FixedClock):
        clock.set("2026-10-02 09:00:01")
        response = book(client, "09:00", "10:00")
        assert response.status_code == 409
        assert error_code(response) == "in_the_past"

    def test_start_equal_to_now_is_allowed(self, client: TestClient, clock: FixedClock):
        clock.set("2026-10-02 09:00:00")
        booked(client, "09:00", "10:00")

    def test_timestamps_in_another_offset_are_converted(self, client: TestClient):
        # 16:30+05:30 is 6:00 AM Central on 2026-10-02.
        body = payload("06:00", "07:00") | {
            "startTime": "2026-10-02T16:30:00+05:30",
            "endTime": "2026-10-02T17:30:00+05:30",
        }
        response = client.post("/api/bookings", json=body)
        assert response.status_code == 201
        assert response.json()["startTime"] == "2026-10-02T06:00:00-05:00"

    @pytest.mark.parametrize(
        ("start", "end", "code"),
        [
            ("05:30", "06:30", "outside_operating_hours"),
            ("21:30", "22:30", "outside_operating_hours"),
            ("06:15", "07:15", "not_on_grid"),
            ("06:00", "14:30", "invalid_duration"),
            ("07:00", "07:00", "invalid_duration"),
        ],
    )
    def test_rule_violations_are_422(self, client: TestClient, start, end, code):
        response = book(client, start, end)
        assert response.status_code == 422
        assert error_code(response) == code

    def test_non_zero_seconds_rejected(self, client: TestClient):
        body = payload("06:00", "07:00") | {"startTime": "2026-10-02T06:00:30-05:00"}
        response = client.post("/api/bookings", json=body)
        assert response.status_code == 422
        assert error_code(response) == "not_on_grid"

    @pytest.mark.parametrize("value", ["2026-10-02T06:00:00", "2026-10-02", 1790938800, None])
    def test_timestamp_without_an_offset_is_422(self, client: TestClient, value):
        response = client.post(
            "/api/bookings", json=payload("06:00", "07:00") | {"startTime": value}
        )
        assert response.status_code == 422
        assert error_code(response) == "validation_error"
        assert "startTime" in response.json()["error"]["message"]

    def test_unknown_field_is_422(self, client: TestClient):
        response = client.post("/api/bookings", json=payload("06:00", "07:00") | {"status": "x"})
        assert response.status_code == 422
        assert error_code(response) == "validation_error"

    def test_unknown_ship_is_404(self, client: TestClient):
        response = book(client, "06:00", "07:00", ship_id=99)
        assert response.status_code == 404
        assert error_code(response) == "not_found"

    def test_pilot_name_limits(self, client: TestClient):
        booked(client, "06:00", "07:00", pilot="x" * 100)
        booked(client, "08:00", "09:00", pilot="  " + "x" * 100 + "  ")  # 100 after trimming
        for pilot in ["x" * 101, "   ", ""]:
            response = book(client, "10:00", "11:00", pilot=pilot)
            assert response.status_code == 422
            assert error_code(response) == "validation_error"

    @pytest.mark.parametrize(
        "change",
        [
            {"shipId": 99999999999},  # too big for the integer column
            {"pilotName": "a\x00b"},
            {"pilotName": "a\nb"},
            {"startTime": "0001-01-01T06:00:00+14:00", "endTime": "0001-01-01T07:00:00+14:00"},
            {"startTime": "9999-12-31T06:00:00-05:00", "endTime": "9999-12-31T07:00:00-05:00"},
        ],
    )
    def test_values_the_database_cannot_hold_are_422(self, client: TestClient, change):
        response = client.post("/api/bookings", json=payload("06:00", "07:00") | change)
        assert response.status_code == 422
        assert error_code(response) == "validation_error"


class TestConcurrency:
    def test_two_simultaneous_bookings_one_wins(self, api, db: Engine, monkeypatch):
        """Hold both requests after the service pre-check, then let them insert together.

        Both pre-checks see a free slot, so only the exclusion constraint can refuse one.
        """
        barrier = threading.Barrier(2, timeout=10)
        real_find_conflicts = bookings_service.find_conflicts
        prechecks_passed = []

        def find_conflicts_then_wait(*args, **kwargs):
            conflicts = real_find_conflicts(*args, **kwargs)
            prechecks_passed.append(conflicts == [])
            barrier.wait()
            return conflicts

        monkeypatch.setattr(bookings_service, "find_conflicts", find_conflicts_then_wait)

        def post(body: dict):
            return TestClient(app).post("/api/bookings", json=body)

        # Overlapping, not identical: 08:00-10:00 and 09:00-11:00.
        bodies = [payload("08:00", "10:00", pilot="A"), payload("09:00", "11:00", pilot="B")]
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(post, bodies))

        assert prechecks_passed == [True, True]
        assert sorted(r.status_code for r in responses) == [201, 409]
        loser = next(r for r in responses if r.status_code == 409)
        assert error_code(loser) == "booking_conflict"
        assert booking_count(db) == 1

    def test_request_after_a_constraint_failure_succeeds(self, client: TestClient, db, monkeypatch):
        booked(client, "08:00", "10:00")
        with monkeypatch.context() as patch:
            patch.setattr(bookings_service, "find_conflicts", lambda *a, **k: [])
            response = book(client, "09:00", "11:00")
        assert response.status_code == 409
        assert error_code(response) == "booking_conflict"

        booked(client, "12:00", "13:00")
        assert booking_count(db) == 2


class TestAvailability:
    def test_shape(self, client: TestClient):
        response = client.get("/api/ships/1/availability", params={"date": DAY})
        body = response.json()

        assert response.status_code == 200
        assert {k: v for k, v in body.items() if k != "slots"} == {
            "shipId": 1,
            "date": "2026-10-02",
            "timezone": "America/Chicago",
            "serverNow": "2026-10-01T21:44:12-05:00",
            "durationMinutes": 60,  # the default
            "lastStart": "2026-10-02T21:00:00-05:00",
        }
        assert len(body["slots"]) == 31
        assert body["slots"][0] == {
            "start": "2026-10-02T06:00:00-05:00",
            "end": "2026-10-02T07:00:00-05:00",
            "available": True,
            "reason": None,
        }
        assert body["slots"][-1]["end"] == "2026-10-02T22:00:00-05:00"
        assert all(slot["available"] for slot in body["slots"])

    def test_booked_and_buffer_slots(self, client: TestClient):
        booked(client, "10:00", "12:00")
        slots = slots_by_start(client)

        reasons = {start: slot["reason"] for start, slot in slots.items() if not slot["available"]}
        assert reasons == {
            "09:00": "buffer",  # ends as the booking starts
            "09:30": "booked",  # starts free, runs into the booking
            "10:00": "booked",
            "10:30": "booked",
            "11:00": "booked",
            "11:30": "booked",
            "12:00": "buffer",  # starts as the booking ends
        }
        assert slots["08:30"]["available"] and slots["12:30"]["available"]

    def test_past_slots_and_precedence(self, client: TestClient, clock: FixedClock):
        booked(client, "10:00", "12:00")
        clock.set("2026-10-02 12:15")
        slots = slots_by_start(client)

        assert slots["06:00"]["reason"] == "past"
        assert slots["11:00"]["reason"] == "past"  # also booked
        assert slots["12:00"]["reason"] == "past"  # also in the buffer
        assert slots["12:30"]["reason"] is None

    def test_a_future_date_has_no_past_slots(self, client: TestClient, clock: FixedClock):
        clock.set("2026-10-02 23:30")
        assert all(slot["available"] for slot in slots_by_start(client, day="2026-10-03").values())
        assert all(slot["reason"] == "past" for slot in slots_by_start(client).values())

    def test_availability_agrees_with_create(self, client: TestClient, db: Engine):
        """Every slot marked available can be booked, and every other slot is refused."""
        booked(client, "10:00", "12:00")
        for duration in (30, 90, 480):
            for slot in slots_by_start(client, duration=duration).values():
                body = payload("06:00", "07:00") | {
                    "startTime": slot["start"],
                    "endTime": slot["end"],
                }
                response = client.post("/api/bookings", json=body)
                assert response.status_code == (201 if slot["available"] else 409), slot
                if response.status_code == 201:
                    # Remove it again so each slot is tried against the same day.
                    with db.begin() as conn:
                        conn.execute(text("DELETE FROM bookings WHERE id = :id"), response.json())

    def test_other_ship_and_other_day_do_not_affect_it(self, client: TestClient):
        booked(client, "10:00", "12:00", ship_id=2)
        booked(client, "10:00", "12:00", day="2026-10-03")
        assert all(slot["available"] for slot in slots_by_start(client).values())

    def test_duration_changes_the_grid(self, client: TestClient):
        slots = slots_by_start(client, duration=480)
        assert list(slots)[-1] == "14:00"
        assert len(slots) == 17

    def test_dst_day_uses_the_new_offset(self, client: TestClient):
        slots = slots_by_start(client, day="2026-11-01", duration=30)
        assert slots["06:00"]["start"] == "2026-11-01T06:00:00-06:00"
        assert len(slots) == 32

    def test_unknown_ship_is_404(self, client: TestClient):
        response = client.get("/api/ships/99/availability", params={"date": DAY})
        assert response.status_code == 404
        assert error_code(response) == "not_found"

    def test_ship_id_too_big_for_the_column_is_422(self, client: TestClient):
        response = client.get("/api/ships/99999999999/availability", params={"date": DAY})
        assert response.status_code == 422
        assert error_code(response) == "validation_error"

    @pytest.mark.parametrize(
        ("params", "code"),
        [
            ({}, "validation_error"),
            ({"date": "02/10/2026"}, "validation_error"),
            ({"date": DAY, "durationMinutes": "abc"}, "validation_error"),
            ({"date": DAY, "durationMinutes": 45}, "invalid_duration"),
            ({"date": DAY, "durationMinutes": 510}, "invalid_duration"),
            ({"date": DAY, "durationMinutes": 0}, "invalid_duration"),
            ({"date": DAY, "durationMinutes": 10**20}, "invalid_duration"),
            ({"date": DAY, "durationMinutes": -(10**20)}, "invalid_duration"),
            ({"date": "9999-12-31"}, "validation_error"),
            ({"date": "0001-01-01"}, "validation_error"),
        ],
    )
    def test_bad_params_are_422(self, client: TestClient, params, code):
        response = client.get("/api/ships/1/availability", params=params)
        assert response.status_code == 422
        assert error_code(response) == code


class TestErrorEnvelope:
    def test_unknown_api_path(self, client: TestClient):
        response = client.get("/api/nope")
        assert response.status_code == 404
        assert error_code(response) == "not_found"

    def test_wrong_method(self, client: TestClient):
        response = client.put("/api/ships")
        assert response.status_code == 405
        assert error_code(response) == "validation_error"

    def test_malformed_json(self, client: TestClient):
        response = client.post(
            "/api/bookings", content="{not json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        assert error_code(response) == "validation_error"

    def test_unhandled_exception_is_a_generic_500(self, api, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(bookings_service, "find_conflicts", boom)
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/bookings", json=payload("06:00", "07:00")
        )
        assert response.status_code == 500
        assert error_code(response) == "internal_error"
        assert "secret" not in response.text and "Traceback" not in response.text


def test_time_returns_the_injected_clock_in_central(client: TestClient):
    response = client.get("/api/time")
    assert response.status_code == 200
    assert response.json() == {
        "serverNow": "2026-10-01T21:44:12-05:00",
        "timezone": "America/Chicago",
    }
