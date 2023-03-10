from datetime import datetime, timedelta
from time import sleep

import pytest
from freezegun import freeze_time

from starlite import Request, get
from starlite.config.cache import CacheConfig
from starlite.testing import create_test_client

from . import after_request_handler, slow_handler


@pytest.mark.parametrize("sync_to_thread", (True, False))
def test_default_cache_response(sync_to_thread: bool) -> None:
    with create_test_client(
        route_handlers=[
            get(
                "/cached",
                sync_to_thread=sync_to_thread,
                cache=True,
                type_encoders={
                    int: str
                },  # test pickling issues. see https://github.com/starlite-api/starlite/issues/1096
            )(slow_handler)
        ],
        after_request=after_request_handler,
    ) as client:
        first_response = client.get("/cached")
        assert first_response.status_code == 200

        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier

        second_response = client.get("/cached")

        assert second_response.status_code == 200
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
    with create_test_client(
        route_handlers=[get("/cached-default", cache=True)(slow_handler)],
        after_request=after_request_handler,
        cache_config=CacheConfig(default_expiration=1),
    ) as client:
        first_response = client.get("/cached-default")
        second_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] == second_response.headers["unique-identifier"]
        sleep(1.2)
        third_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]


@pytest.mark.parametrize("sync_to_thread", (True, False))
async def test_custom_cache_key(sync_to_thread: bool, anyio_backend: str) -> None:
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[
            get("/cached", sync_to_thread=sync_to_thread, cache=True, cache_key_builder=custom_cache_key_builder)(
                slow_handler
            )
        ]
    ) as client:
        client.get("/cached")
        value = await client.app.cache_config.storage.get("/cached:::cached")
        assert value
