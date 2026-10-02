from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import error_code


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>spaceport</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path.parent / "secret.txt").write_text("outside the static directory")
    return TestClient(create_app(static_dir=tmp_path))


def test_root_serves_the_app(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "spaceport" in response.text


def test_static_files_are_served(client: TestClient):
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


def test_client_side_routes_fall_back_to_index(client: TestClient):
    for path in ("/fleet", "/fleet/anything", "/assets/missing.js"):
        response = client.get(path)
        assert response.status_code == 200
        assert "spaceport" in response.text


def test_unknown_api_path_is_a_json_404_not_the_app(client: TestClient):
    for path in ("/api/nope", "/api", "/api/"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert error_code(response) == "not_found"


def test_cannot_read_files_outside_the_static_directory(client: TestClient):
    response = client.get("/%2e%2e/secret.txt")
    assert "outside" not in response.text


def test_api_routes_still_win(client: TestClient):
    response = client.get("/api/time")
    assert response.status_code == 200
    assert set(response.json()) == {"serverNow", "timezone"}
