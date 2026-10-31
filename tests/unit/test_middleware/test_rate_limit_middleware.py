from datetime import datetime
from time import time
from typing import TYPE_CHECKING, Any

import pytest
from time_machine import travel

from litestar import Litestar, Request, get
from litestar.handlers import ASGIRouteHandler
from litestar.middleware.rate_limit import (
    DURATION_VALUES,
    CacheObject,
    DurationUnit,
    RateLimitConfig,
    RateLimitMiddleware,
)
from litestar.response.base import ASGIResponse
from litestar.serialization import decode_json, encode_json
from litestar.status_codes import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS
from litestar.stores.base import Store
from litestar.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("unit", ["minute", "second", "hour", "day"])
async def test_rate_limiting(unit: DurationUnit) -> None:
    @get("/")
    def handler() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(rate_limit=(unit, 2))
    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(route_handlers=[handler], middleware=[rate_limit_middleware])
    store = app.stores.get("rate_limit")

    with travel(datetime.utcnow, tick=False) as frozen_time, TestClient(app=app) as client:
        response = client.get("/")

        cached_value = await store.get(cache_key)
        assert cached_value
        cache_object = CacheObject(**decode_json(value=cached_value))
        assert len(cache_object.history) == 1

        assert response.status_code == HTTP_200_OK
        assert (
            response.headers.get(rate_limit_middleware.rate_limit_policy_header_key) == f"2; w={DURATION_VALUES[unit]}"
        )
        assert response.headers.get(rate_limit_middleware.rate_limit_limit_header_key) == "2"
        assert response.headers.get(rate_limit_middleware.rate_limit_remaining_header_key) == "1"
        # Since the time is frozen, no time has passed.
        # Therefore, the remaining seconds for the current quota window should be the same as the entire window length.
        assert response.headers.get(rate_limit_middleware.rate_limit_reset_header_key) == str(DURATION_VALUES[unit])

        # Move time one second before the end of the quota window for the next request
        frozen_time.shift(DURATION_VALUES[unit] - 1)
        response = client.get("/")

        assert response.status_code == HTTP_200_OK
        assert (
            response.headers.get(rate_limit_middleware.rate_limit_policy_header_key) == f"2; w={DURATION_VALUES[unit]}"
        )
        assert response.headers.get(rate_limit_middleware.rate_limit_limit_header_key) == "2"
        assert response.headers.get(rate_limit_middleware.rate_limit_remaining_header_key) == "0"
        assert response.headers.get(rate_limit_middleware.rate_limit_reset_header_key) == "1"

        response = client.get("/")

        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert (
            response.headers.get(rate_limit_middleware.rate_limit_policy_header_key) == f"2; w={DURATION_VALUES[unit]}"
        )
        assert response.headers.get(rate_limit_middleware.rate_limit_limit_header_key) == "2"
        assert response.headers.get(rate_limit_middleware.rate_limit_remaining_header_key) == "0"
        assert response.headers.get(rate_limit_middleware.rate_limit_reset_header_key) == "1"

        # Move time one second so that a new quota window starts
        frozen_time.shift(1)

        response = client.get("/")
        assert response.status_code == HTTP_200_OK


async def test_non_default_store(memory_store: Store) -> None:
    @get("/")
    def handler() -> None:
        return None

    app = Litestar([handler], middleware=[RateLimitMiddleware(("second", 10))], stores={"rate_limit": memory_store})

    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200

    assert await memory_store.exists("RateLimitMiddleware::testclient")


async def test_set_store_name(memory_store: Store) -> None:
    @get("/")
    def handler() -> None:
        return None

    app = Litestar(
        [handler],
        middleware=[RateLimitMiddleware(("second", 10), store="some_store")],
        stores={"some_store": memory_store},
    )

    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200

    assert await memory_store.exists("RateLimitMiddleware::testclient")


async def test_reset() -> None:
    @get("/")
    def handler() -> None:
        return None

    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(route_handlers=[handler], middleware=[RateLimitMiddleware(rate_limit=("second", 1))])
    store = app.stores.get("rate_limit")

    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        cached_value = await store.get(cache_key)
        assert cached_value
        cache_object = CacheObject(**decode_json(value=cached_value))
        assert cache_object.reset == int(time() + 1)

        cache_object.reset -= 2
        await store.set(cache_key, encode_json(cache_object))

        response = client.get("/")
        assert response.status_code == HTTP_200_OK


@travel(datetime.utcnow, tick=False)
def test_exclude_patterns() -> None:
    @get("/excluded")
    def handler() -> None:
        return None

    @get("/not-excluded")
    def handler2() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("second", 1), exclude=["/excluded"])

    with create_test_client(route_handlers=[handler, handler2], middleware=[rate_limit_middleware]) as client:
        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/not-excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/not-excluded")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS


@travel(datetime.utcnow, tick=False)
def test_exclude_opt_key() -> None:
    @get("/excluded", skip_rate_limiting=True)
    def handler() -> None:
        return None

    @get("/not-excluded")
    def handler2() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("second", 1), exclude_opt_key="skip_rate_limiting")

    with create_test_client(route_handlers=[handler, handler2], middleware=[rate_limit_middleware]) as client:
        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/not-excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/not-excluded")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS


@travel(datetime.utcnow, tick=False)
def test_check_throttle_handler() -> None:
    @get("/path1")
    def handler1() -> None:
        return None

    @get("/path2")
    def handler2() -> None:
        return None

    def check_throttle_handler(request: Request[Any, Any, Any]) -> bool:
        return request.url.path == "/path1"

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("minute", 1), check_throttle_handler=check_throttle_handler)

    with create_test_client(route_handlers=[handler1, handler2], middleware=[rate_limit_middleware]) as client:
        response = client.get("/path1")
        assert response.status_code == HTTP_200_OK

        response = client.get("/path1")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        response = client.get("/path2")
        assert response.status_code == HTTP_200_OK

        response = client.get("/path2")
        assert response.status_code == HTTP_200_OK


@travel(datetime.utcnow, tick=False)
async def test_rate_limiting_works_with_mounted_apps(tmpdir: "Path") -> None:
    # https://github.com/litestar-org/litestar/issues/781
    @get("/not-excluded")
    def handler() -> None:
        return None

    path1 = tmpdir / "test.css"
    path1.write_text("styles content", "utf-8")

    asgi_handler = ASGIRouteHandler("/asgi", is_mount=True, fn=ASGIResponse(body="something"))

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("minute", 1), exclude=[r"^/src.*$"])
    with create_test_client([handler, asgi_handler], middleware=[rate_limit_middleware]) as client:
        response = client.get("/not-excluded")
        assert response.status_code == HTTP_200_OK

        response = client.get("/not-excluded")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        response = client.get("/asgi")
        assert response.status_code == HTTP_200_OK
        assert response.text == "something"


async def test_rate_limiting_works_with_cache() -> None:
    @get("/", cache=True)
    def handler() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("minute", 2))
    app = Litestar(route_handlers=[handler], middleware=[rate_limit_middleware])

    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.headers.get(rate_limit_middleware.rate_limit_remaining_header_key) == "1"

        response = client.get("/")
        assert response.headers.get(rate_limit_middleware.rate_limit_remaining_header_key) == "0"

        response = client.get("/")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS


def test_ignore_x_forwarded_for() -> None:
    @get("/")
    def handler() -> None:
        return None

    app = Litestar(
        route_handlers=[handler],
        middleware=[RateLimitMiddleware(rate_limit=("minute", 2))],
    )

    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        # this shouldn't have any effect
        response = client.get("/", headers={"x-forwarded-for": "1.2.3.4"})
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS


def test_custom_identity_function() -> None:
    @get("/")
    def handler() -> None:
        return None

    def get_id_from_random_header(request: Request[Any, Any, Any]) -> str:
        return request.headers["x-private-header"]

    app = Litestar(
        route_handlers=[handler],
        middleware=[RateLimitMiddleware(rate_limit=("minute", 2), identifier_for_request=get_id_from_random_header)],
    )

    with TestClient(app=app) as client:
        response = client.get("/", headers={"x-private-header": "value"})
        assert response.status_code == HTTP_200_OK
        response = client.get("/", headers={"x-private-header": "value"})
        assert response.status_code == HTTP_200_OK

        response = client.get("/", headers={"x-private-header": "value"})
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        # a different identity gets its own quota, even though the remote address is the same
        response = client.get("/", headers={"x-private-header": "other-value"})
        assert response.status_code == HTTP_200_OK


@travel(datetime.utcnow, tick=False)
def test_set_rate_limit_headers_disabled() -> None:
    @get("/")
    def handler() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(rate_limit=("second", 1), set_rate_limit_headers=False)

    with create_test_client(route_handlers=[handler], middleware=[rate_limit_middleware]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert rate_limit_middleware.rate_limit_policy_header_key not in response.headers
        assert rate_limit_middleware.rate_limit_limit_header_key not in response.headers
        assert rate_limit_middleware.rate_limit_remaining_header_key not in response.headers
        assert rate_limit_middleware.rate_limit_reset_header_key not in response.headers

        response = client.get("/")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert rate_limit_middleware.rate_limit_limit_header_key not in response.headers


@travel(datetime.utcnow, tick=False)
def test_custom_header_keys() -> None:
    @get("/")
    def handler() -> None:
        return None

    rate_limit_middleware = RateLimitMiddleware(
        rate_limit=("minute", 2),
        rate_limit_policy_header_key="X-Policy",
        rate_limit_limit_header_key="X-Limit",
        rate_limit_remaining_header_key="X-Remaining",
        rate_limit_reset_header_key="X-Reset",
    )

    with create_test_client(route_handlers=[handler], middleware=[rate_limit_middleware]) as client:
        response = client.get("/")
        assert response.headers.get("X-Policy") == "2; w=60"
        assert response.headers.get("X-Limit") == "2"
        assert response.headers.get("X-Remaining") == "1"
        assert response.headers.get("X-Reset") == "60"


@travel(datetime.utcnow, tick=False)
def test_mounted_apps_are_rate_limited() -> None:
    asgi_handler = ASGIRouteHandler("/asgi", is_mount=True, fn=ASGIResponse(body="something"))

    with create_test_client([asgi_handler], middleware=[RateLimitMiddleware(rate_limit=("minute", 1))]) as client:
        response = client.get("/asgi")
        assert response.status_code == HTTP_200_OK

        response = client.get("/asgi")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS


@travel(datetime.utcnow, tick=False)
def test_exclude_matches_handler_path_template() -> None:
    from litestar.params import FromPath

    @get("/user/{user_id:int}")
    def excluded_handler(user_id: FromPath[int]) -> None:
        return None

    @get("/order/{order_id:int}")
    def limited_handler(order_id: FromPath[int]) -> None:
        return None

    # exclusion patterns match the handler's path template, not the request path
    rate_limit_middleware = RateLimitMiddleware(rate_limit=("second", 1), exclude=[r"/user/\{user_id:int\}"])

    with create_test_client(
        route_handlers=[excluded_handler, limited_handler], middleware=[rate_limit_middleware]
    ) as client:
        assert client.get("/user/1").status_code == HTTP_200_OK
        assert client.get("/user/1").status_code == HTTP_200_OK

        assert client.get("/order/1").status_code == HTTP_200_OK
        assert client.get("/order/1").status_code == HTTP_429_TOO_MANY_REQUESTS


def test_config_middleware_property_deprecated() -> None:
    config = RateLimitConfig(rate_limit=("minute", 2), store="some_store")

    with pytest.warns(DeprecationWarning, match="RateLimitConfig.middleware"):
        middleware = config.middleware

    assert isinstance(middleware, RateLimitMiddleware)
    assert middleware.store == "some_store"
