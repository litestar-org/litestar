from unittest.mock import patch

from docs.examples.datastructures.headers.cache_control import app as cache_control_app
from docs.examples.datastructures.headers.etag import app as etag_app

from litestar.testing import TestClient


def test_cache_control_population() -> None:
    with TestClient(app=cache_control_app) as client:
        res = client.get("/population")
        assert res.status_code == 200
        assert res.headers["cache-control"] == "max-age=2628288, public"


def test_cache_control_chance_of_rain() -> None:
    with TestClient(app=cache_control_app) as client:
        res = client.get("/chance_of_rain")
        assert res.status_code == 200
        assert res.headers["cache-control"] == "max-age=86400, public"


def test_cache_control_timestamp() -> None:
    with TestClient(app=cache_control_app) as client:
        res = client.get("/timestamp")
        assert res.status_code == 200
        assert res.headers["cache-control"] == "no-store"


def test_etag_chance_of_rain() -> None:
    with TestClient(app=etag_app) as client:
        res = client.get("/chance_of_rain")
        assert res.status_code == 200
        assert res.headers["etag"] == '"foo"'


def test_etag_timestamp() -> None:
    with TestClient(app=etag_app) as client:
        res = client.get("/timestamp")
        assert res.status_code == 200
        assert res.headers["etag"] == 'W/"bar"'


def test_etag_population() -> None:
    with TestClient(app=etag_app) as client:
        res = client.get("/population")
        assert res.status_code == 200
        assert res.headers["etag"] == '"bar"'


def test_etag_population_dynamic() -> None:
    with TestClient(app=etag_app) as client, patch("random.randint") as mock_randint:
        mock_randint.return_value = 42
        res = client.get("/population-dynamic")
        assert res.status_code == 200
        assert res.headers["etag"] == '"42"'
