from typing import Any

import pytest
from orjson import dumps, loads
from starlette.status import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS

from starlite import Request, get
from starlite.middleware.rate_limit import (
    DURATION_VALUES,
    DurationUnit,
    RateLimitConfig,
)
from starlite.testing import create_test_client


@pytest.mark.parametrize("unit", ["minute", "second", "hour", "day"])
async def test_rate_limiting(unit: DurationUnit) -> None:
    @get("/")
    def handler() -> None:
        return None

    config = RateLimitConfig(rate_limit=(unit, 1))
    cache_key = "RateLimitMiddleware::testclient"

    with create_test_client(route_handlers=[handler], middleware=[config.middleware]) as client:
        cache = client.app.cache
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        cached_value = await cache.get(cache_key)
        cached_list = loads(cached_value)
        assert len(cached_list) == 1

        response = client.get("/")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        await cache.set(cache_key, dumps([cached_list[0] - DURATION_VALUES[unit]]))
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


def test_exclude() -> None:
    @get("/excluded")
    def handler() -> None:
        return None

    config = RateLimitConfig(rate_limit=("second", 1), exclude=["excluded"])

    with create_test_client(route_handlers=[handler], middleware=[config.middleware]) as client:
        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK


def test_check_throttle_handler() -> None:
    @get("/path1")
    def handler1() -> None:
        return None

    @get("/path2")
    def handler2() -> None:
        return None

    def check_throttle_handler(request: Request[Any, Any]) -> bool:
        return request.url.path == "/path1"

    config = RateLimitConfig(rate_limit=("second", 1), check_throttle_handler=check_throttle_handler)

    with create_test_client(route_handlers=[handler1, handler2], middleware=[config.middleware]) as client:
        response = client.get("/path1")
        assert response.status_code == HTTP_200_OK

        response = client.get("/path1")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        response = client.get("/path2")
        assert response.status_code == HTTP_200_OK

        response = client.get("/path2")
        assert response.status_code == HTTP_200_OK
