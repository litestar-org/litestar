import random
from datetime import datetime, timedelta
from time import sleep
from typing import Any
from uuid import uuid4

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from starlite import CacheConfig, Request, Response, get
from starlite.cache import SimpleCacheBackend
from starlite.testing import create_test_client


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


def test_cache_key() -> None:
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[get("/cached", cache=True, cache_key_builder=custom_cache_key_builder)(slow_handler)]
    ) as client:
        client.get("/cached")
        assert client.app.cache_config.backend.get("/cached:::cached")  # type: ignore


def test_async_handling() -> None:
    class AsyncCacheBackend(SimpleCacheBackend):
        async def set(self, key: str, value: Any, expiration: int) -> Any:  # type: ignore
            super().set(key=key, value=value, expiration=expiration)

        async def get(self, key: str) -> Any:
            return super().get(key=key)

    cache_config = CacheConfig(backend=AsyncCacheBackend())

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


def test_config_validation() -> None:
    class MyBackend:
        def get(self) -> None:
            ...

        def set(self) -> None:
            ...

    with pytest.raises(ValidationError):
        CacheConfig(backend=MyBackend)  # type: ignore[arg-type]


def test_naive_cache_backend() -> None:
    backend = SimpleCacheBackend()
    backend.set("test", "1", 0.1)  # type: ignore
    assert backend.get("test")
    sleep(0.2)
    assert not backend.get("test")
