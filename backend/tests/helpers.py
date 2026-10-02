"""Shared request helpers for the API tests. Bookings default to 2026-10-02 (CDT)."""

from fastapi.testclient import TestClient

DAY = "2026-10-02"


def at(hhmm: str, day: str = DAY) -> str:
    return f"{day}T{hhmm}:00-05:00"


def payload(start: str, end: str, *, ship_id: int = 1, pilot: str = "Naomi Nagata",
            day: str = DAY) -> dict:  # fmt: skip
    return {
        "shipId": ship_id,
        "pilotName": pilot,
        "startTime": at(start, day),
        "endTime": at(end, day),
    }


def book(client: TestClient, start: str, end: str, **kwargs):
    return client.post("/api/bookings", json=payload(start, end, **kwargs))


def booked(client: TestClient, start: str, end: str, **kwargs) -> dict:
    response = book(client, start, end, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def error_code(response) -> str:
    body = response.json()
    assert set(body) == {"error"}, body
    assert set(body["error"]) == {"code", "message"}, body
    assert body["error"]["message"]
    return body["error"]["code"]
