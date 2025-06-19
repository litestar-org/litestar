import datetime as dt

import pytest
from time_machine import travel

from litestar import Litestar, get
from litestar.controller import Controller
from litestar.middleware.rate_limit import CacheObject, RateLimitConfig
from litestar.serialization import decode_json
from litestar.status_codes import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS
from litestar.testing import TestClient


@pytest.mark.xfail()
async def test_my_rate_limiting_failure() -> None:
    @get("/ham", middleware=[RateLimitConfig(("minute", 1000)).middleware])
    async def can_go_ham() -> None:
        return None

    @get("/cheese", middleware=[RateLimitConfig(("hour", 1)).middleware])
    async def dont_go_ham() -> None:
        return None

    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(route_handlers=[can_go_ham, dont_go_ham])
    store = app.stores.get("rate_limit")

    with travel(dt.datetime.now(tz=dt.timezone.utc), tick=False), TestClient(app=app) as client:
        response = client.get("/ham")
        assert response.status_code == HTTP_200_OK

        response = client.get("/cheese")
        cached_value = await store.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        assert response.status_code == HTTP_200_OK, cache_object.history  # <-- fails here


async def test_my_rate_limiting() -> None:
    @get("/ham", middleware=[RateLimitConfig(("hour", 1000), store="rl1").middleware])
    async def can_go_ham() -> None:
        return None

    @get("/cheese", middleware=[RateLimitConfig(("hour", 1), store="rl2").middleware])
    async def dont_go_ham() -> None:
        return None

    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(route_handlers=[can_go_ham, dont_go_ham])
    store1 = app.stores.get("rl1")
    store2 = app.stores.get("rl2")

    with travel(dt.datetime.now(tz=dt.timezone.utc), tick=False), TestClient(app=app) as client:
        response = client.get("/ham")
        assert response.status_code == HTTP_200_OK
        cached_value = await store1.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        print(cache_object.history)

        response = client.get("/cheese")
        assert response.status_code == HTTP_200_OK
        cached_value = await store2.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        print(cache_object.history)

        response = client.get("/cheese")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        cached_value = await store2.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        print(cache_object.history)


@pytest.mark.xfail()
async def test_multiple_entries_on_the_way_in() -> None:
    class MyController(Controller):
        middleware = [RateLimitConfig(("hour", 2)).middleware]

        @get("/", middleware=[RateLimitConfig(("hour", 2)).middleware])
        async def handler(self) -> None:
            return None

    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(
        route_handlers=[MyController],
        middleware=[RateLimitConfig(("hour", 2)).middleware],
    )
    store = app.stores.get("rate_limit")

    with travel(dt.datetime.now(tz=dt.timezone.utc), tick=False), TestClient(app=app) as client:
        response = client.get("/")
        cached_value = await store.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        # because everything is cached to the same key in the same store, fails here
        assert response.status_code == HTTP_200_OK, cache_object.history


async def test_multiple_entries_on_the_way_in_fix() -> None:
    class MyController(Controller):
        middleware = [RateLimitConfig(("hour", 2)).middleware]

        @get("/", middleware=[RateLimitConfig(("hour", 2)).middleware])
        async def handler(self) -> None:
            return None

    cache_key = "RateLimitMiddleware::testclient"
    app = Litestar(
        route_handlers=[MyController],
        middleware=[RateLimitConfig(("hour", 2)).middleware],
    )
    store = app.stores.get("rate_limit")

    with travel(dt.datetime.now(tz=dt.timezone.utc), tick=False), TestClient(app=app) as client:
        response = client.get("/")
        cached_value = await store.get(cache_key)
        assert cached_value is not None
        cache_object = CacheObject(**decode_json(value=cached_value))
        assert response.status_code == HTTP_200_OK, cache_object.history
