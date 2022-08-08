from datetime import datetime, timedelta

from freezegun import freeze_time

from starlite import Request, get
from starlite.testing import create_test_client

from . import after_request_handler, slow_handler


def test_default_cache_response() -> None:
    with create_test_client(
        route_handlers=[get("/cached", cache=True)(slow_handler)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()


def test_handler_expiration() -> None:
    now = datetime.now()
    with freeze_time(now) as frozen_datetime, create_test_client(
        route_handlers=[get("/cached-local", cache=10)(slow_handler)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached-local")
        frozen_datetime.tick(delta=timedelta(seconds=5))
        second_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] == second_response.headers["unique-identifier"]
        frozen_datetime.tick(delta=timedelta(seconds=11))
        third_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]


def test_default_expiration() -> None:
    now = datetime.now()
    with freeze_time(now) as frozen_datetime, create_test_client(
        route_handlers=[get("/cached-default", cache=True)(slow_handler)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached-default")
        frozen_datetime.tick(delta=timedelta(seconds=30))
        second_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] == second_response.headers["unique-identifier"]
        frozen_datetime.tick(delta=timedelta(seconds=61))
        third_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]


def test_custom_cache_key() -> None:
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[get("/cached", cache=True, cache_key_builder=custom_cache_key_builder)(slow_handler)]
    ) as client:
        client.get("/cached")
        assert client.app.cache_config.backend.get("/cached:::cached")
