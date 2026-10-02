"""Bookings list, nearest-dates and cancel, through the API against real Postgres."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.main import app
from tests.conftest import FixedClock
from tests.helpers import DAY, book, booked, error_code


def listing(client: TestClient, first=DAY, last=DAY, **params) -> list[dict]:
    response = client.get("/api/bookings", params={"from": first, "to": last, **params})
    assert response.status_code == 200, response.text
    return response.json()


def cancel(client: TestClient, booking_id: int):
    return client.delete(f"/api/bookings/{booking_id}")


def nearest(client: TestClient, day: str, **params) -> dict:
    response = client.get("/api/bookings/nearest-dates", params={"date": day, **params})
    assert response.status_code == 200, response.text
    return response.json()


class TestCancel:
    def test_returns_the_cancelled_booking(self, client: TestClient):
        booking = booked(client, "08:00", "10:00")
        response = cancel(client, booking["id"])

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "cancelled"
        assert body["cancelledAt"] is not None and body["cancelledAt"][-6:] in ("-05:00", "-06:00")
        assert {k: body[k] for k in body if k not in ("status", "cancelledAt")} == {
            k: booking[k] for k in booking if k not in ("status", "cancelledAt")
        }

    def test_freed_slot_can_be_booked_again(self, client: TestClient):
        booking = booked(client, "08:00", "10:00")
        assert book(client, "08:00", "10:00").status_code == 409
        cancel(client, booking["id"])

        replacement = booked(client, "08:00", "10:00", pilot="Bobbie Draper")
        assert replacement["id"] != booking["id"]

    def test_freed_slot_shows_as_available(self, client: TestClient):
        booking = booked(client, "08:00", "10:00")
        cancel(client, booking["id"])
        slots = client.get("/api/ships/1/availability", params={"date": DAY}).json()["slots"]
        assert all(slot["available"] for slot in slots)

    def test_booking_in_progress_is_409_already_started(self, client: TestClient, clock):
        booking = booked(client, "08:00", "10:00")
        clock.set("2026-10-02 09:00")
        response = cancel(client, booking["id"])
        assert response.status_code == 409
        assert error_code(response) == "already_started"

    def test_booking_starting_exactly_now_cannot_be_cancelled(self, client, clock: FixedClock):
        booking = booked(client, "08:00", "10:00")
        clock.set("2026-10-02 08:00:00")
        assert error_code(cancel(client, booking["id"])) == "already_started"

    def test_one_second_before_start_can_be_cancelled(self, client, clock: FixedClock):
        booking = booked(client, "08:00", "10:00")
        clock.set("2026-10-02 07:59:59")
        assert cancel(client, booking["id"]).status_code == 200

    def test_finished_booking_is_409_already_started(self, client: TestClient, clock):
        booking = booked(client, "08:00", "10:00")
        clock.set("2026-10-03 12:00")
        assert error_code(cancel(client, booking["id"])) == "already_started"

    def test_cancelling_twice_is_409_already_cancelled(self, client: TestClient):
        booking = booked(client, "08:00", "10:00")
        cancel(client, booking["id"])
        response = cancel(client, booking["id"])
        assert response.status_code == 409
        assert error_code(response) == "already_cancelled"

    def test_unknown_booking_is_404(self, client: TestClient):
        response = cancel(client, 999)
        assert response.status_code == 404
        assert error_code(response) == "not_found"

    def test_non_numeric_id_is_422(self, client: TestClient):
        response = client.delete("/api/bookings/abc")
        assert response.status_code == 422
        assert error_code(response) == "validation_error"

    def test_two_simultaneous_cancels_one_wins(self, client: TestClient, db: Engine):
        booking = booked(client, "08:00", "10:00")
        barrier = threading.Barrier(2, timeout=10)

        def cancel_together(_):
            barrier.wait()
            return TestClient(app).delete(f"/api/bookings/{booking['id']}")

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(cancel_together, range(2)))

        assert sorted(r.status_code for r in responses) == [200, 409]
        loser = next(r for r in responses if r.status_code == 409)
        assert error_code(loser) == "already_cancelled"


class TestList:
    def test_ordered_by_ship_then_start_then_id(self, client: TestClient):
        late = booked(client, "15:00", "16:00", ship_id=1)
        other_ship = booked(client, "06:00", "07:00", ship_id=2)
        early = booked(client, "08:00", "09:00", ship_id=1)
        # A cancelled booking and its replacement share ship and start: id breaks the tie.
        cancel(client, early["id"])
        rebooked = booked(client, "08:00", "09:00", ship_id=1)

        ids = [b["id"] for b in listing(client, includeCancelled=True)]
        assert ids == [early["id"], rebooked["id"], late["id"], other_ship["id"]]

    def test_cancelled_are_hidden_by_default(self, client: TestClient):
        kept = booked(client, "06:00", "07:00")
        gone = booked(client, "09:00", "10:00")
        cancel(client, gone["id"])

        assert [b["id"] for b in listing(client)] == [kept["id"]]
        with_cancelled = listing(client, includeCancelled=True)
        assert [(b["id"], b["status"]) for b in with_cancelled] == [
            (kept["id"], "active"),
            (gone["id"], "cancelled"),
        ]

    def test_range_is_inclusive_central_dates(self, client: TestClient):
        booked(client, "21:00", "22:00", day="2026-10-02")  # 03:00 UTC on the 3rd
        booked(client, "06:00", "07:00", day="2026-10-03")
        booked(client, "06:00", "07:00", day="2026-10-04")

        def starts(first, last):
            return [b["startTime"][:16] for b in listing(client, first, last)]

        assert starts("2026-10-02", "2026-10-02") == ["2026-10-02T21:00"]
        assert starts("2026-10-03", "2026-10-03") == ["2026-10-03T06:00"]
        assert starts("2026-10-02", "2026-10-04") == [
            "2026-10-02T21:00",
            "2026-10-03T06:00",
            "2026-10-04T06:00",
        ]
        assert starts("2026-10-05", "2026-10-05") == []

    def test_filter_by_ship(self, client: TestClient):
        booked(client, "06:00", "07:00", ship_id=1)
        mine = booked(client, "06:00", "07:00", ship_id=2)
        assert [b["id"] for b in listing(client, shipId=2)] == [mine["id"]]

    def test_unknown_ship_is_404(self, client: TestClient):
        response = client.get("/api/bookings", params={"from": DAY, "to": DAY, "shipId": 99})
        assert response.status_code == 404
        assert error_code(response) == "not_found"

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"from": DAY},
            {"to": DAY},
            {"from": "2026-10-03", "to": "2026-10-02"},  # from > to
            {"from": "2026-10-01", "to": "2026-11-01"},  # 32 dates
            {"from": "yesterday", "to": DAY},
            {"from": DAY, "to": DAY, "shipId": "x"},
        ],
    )
    def test_bad_params_are_422(self, client: TestClient, params):
        response = client.get("/api/bookings", params=params)
        assert response.status_code == 422
        assert error_code(response) == "validation_error"

    def test_31_dates_is_allowed(self, client: TestClient):
        assert listing(client, "2026-10-01", "2026-10-31") == []


class TestNearestDates:
    def test_both_null_when_there_are_no_bookings(self, client: TestClient):
        assert nearest(client, DAY) == {"previous": None, "next": None}

    def test_previous_and_next(self, client: TestClient, db: Engine):
        with db.begin() as conn:  # history, inserted directly: the API refuses past bookings
            conn.execute(
                text(
                    "INSERT INTO bookings (ship_id, pilot_name, start_time, end_time) VALUES "
                    "(1, 'P', '2026-06-05T21:00-05:00', '2026-06-05T22:00-05:00'), "
                    "(2, 'P', '2026-05-20T08:00-05:00', '2026-05-20T09:00-05:00')"
                )
            )
        booked(client, "06:00", "07:00", day="2026-10-02")
        booked(client, "06:00", "07:00", day="2026-10-09")

        assert nearest(client, "2026-10-05") == {"previous": "2026-10-02", "next": "2026-10-09"}
        # The viewed day's own bookings don't count in either direction.
        assert nearest(client, "2026-10-02") == {"previous": "2026-06-05", "next": "2026-10-09"}
        # 9:00 PM Central on June 5 is already June 6 in UTC: it must still read as June 5.
        assert nearest(client, "2026-06-06") == {"previous": "2026-06-05", "next": "2026-10-02"}
        assert nearest(client, "2026-06-05") == {"previous": "2026-05-20", "next": "2026-10-02"}
        assert nearest(client, "2026-12-01") == {"previous": "2026-10-09", "next": None}
        assert nearest(client, "2026-01-01") == {"previous": None, "next": "2026-05-20"}

    def test_cancelled_days_count_only_when_asked(self, client: TestClient):
        booking = booked(client, "06:00", "07:00", day="2026-10-09")
        cancel(client, booking["id"])

        assert nearest(client, DAY) == {"previous": None, "next": None}
        assert nearest(client, DAY, includeCancelled=True) == {
            "previous": None,
            "next": "2026-10-09",
        }

    def test_missing_date_is_422(self, client: TestClient):
        response = client.get("/api/bookings/nearest-dates")
        assert response.status_code == 422
        assert error_code(response) == "validation_error"
