import random
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from starlite import CacheConfig, Request, Response, create_test_client, get
from starlite.caching import SimpleCacheBackend


async def slow_handler() -> dict:
    output = {}
    count = 0
    while count < 1000:
        output[str(count)] = random.random()
        count += 1
    return output


def after_request_handler(response: Response) -> Response:
    response.headers["unique-identifier"] = str(uuid4())
    return response


def test_default_cache_response():
    with create_test_client(
        route_handlers=[get("/cached", cache=True)(slow_handler)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()


def test_handler_expiration():
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


def test_default_expiration():
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


def test_cache_key():
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[get("/cached", cache=True, cache_key_builder=custom_cache_key_builder)(slow_handler)]
    ) as client:
        client.get("/cached")
        assert client.app.cache_config.backend.get("/cached:::cached")


def test_async_handling():
    class AsyncCacheBackend(SimpleCacheBackend):
        async def set(self, key: str, value: Any, expiration: int) -> None:
            return super().set(key=key, value=value, expiration=expiration)

        async def get(self, key: str) -> Any:
            return super().get(key=key)

    cache_config = CacheConfig(backend=AsyncCacheBackend)

    with create_test_client(
        route_handlers=[get("/cached-async", cache=True)(slow_handler)],
        after_request=after_request_handler,
        cache_config=cache_config,
    ) as client:
        first_response = client.get("/cached-async")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached-async")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()


def test_config_validation():
    class MyBackend:
        def get(self):
            ...

        def set(self):
            ...

    with pytest.raises(ValidationError):
        CacheConfig(backend=MyBackend)
