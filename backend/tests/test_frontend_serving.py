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


def test_hashed_assets_are_cached_for_good_and_the_page_is_not(client: TestClient):
    assert "immutable" in client.get("/assets/app.js").headers["cache-control"]
    # index.html names the current hashed files, so it must be revalidated every time,
    # including when it stands in for an asset that no longer exists.
    for path in ("/", "/fleet", "/assets/missing.js"):
        assert client.get(path).headers["cache-control"] == "no-cache", path


def test_large_responses_are_compressed(client: TestClient, tmp_path: Path):
    (tmp_path / "assets" / "big.js").write_text("console.log('app')\n" * 500)
    response = client.get("/assets/big.js", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert response.text.startswith("console.log")


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
