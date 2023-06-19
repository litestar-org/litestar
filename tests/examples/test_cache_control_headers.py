from docs.examples.datastructures.headers import cache_control

from litestar.testing import TestClient


def test_cache_control_header() -> None:
    with TestClient(app=cache_control.app) as client:
        response = client.get("/population")
        assert response.headers["cache-control"] in ("max-age=2628288, public", "public, max-age=2628288")

        response = client.get("/chance_of_rain")
        assert response.headers["cache-control"] in ("max-age=86400, public", "public, max-age=86400")

        response = client.get("/timestamp")
        assert response.headers["cache-control"] == "no-store"
