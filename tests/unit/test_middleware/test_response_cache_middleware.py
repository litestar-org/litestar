from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import anyio

from litestar import asgi, get
from litestar.config.response_cache import ResponseCacheConfig
from litestar.params import FromPath
from litestar.testing import create_async_test_client, create_test_client

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types import Receive, Scope, Send
    from litestar.types.asgi_types import HTTPResponseBodyEvent, HTTPResponseStartEvent


async def test_handler_cache_key_builder_takes_precedence_over_the_config() -> None:
    def config_key_builder(request: Request[Any, Any, Any]) -> str:  # pragma: no cover
        return "from-config"

    def handler_key_builder(request: Request[Any, Any, Any]) -> str:
        return "from-handler"

    @get("/cached", cache=True, cache_key_builder=handler_key_builder)
    async def handler() -> str:
        return "value"

    config = ResponseCacheConfig(key_builder=config_key_builder)

    async with create_async_test_client([handler], response_cache_config=config) as client:
        await client.get("/cached")
        store = client.app.stores.get("response_cache")

        assert await store.exists("from-handler")
        assert not await store.exists("from-config")


def test_middleware_is_not_applied_to_asgi_routes(response_cache_handle: MagicMock) -> None:
    @asgi("/asgi")
    async def asgi_handler(scope: Scope, receive: Receive, send: Send) -> None:
        start: HTTPResponseStartEvent = {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
        body: HTTPResponseBodyEvent = {"type": "http.response.body", "body": b"value", "more_body": False}
        await send(start)
        await send(body)

    @get("/cached", cache=True)
    def cached_handler() -> str:
        return "value"

    with create_test_client([asgi_handler, cached_handler]) as client:
        assert client.get("/asgi").text == "value"
        response_cache_handle.assert_not_called()

        client.get("/cached")
        response_cache_handle.assert_called_once_with("/cached")


def test_middleware_does_not_leak_state_between_sequential_requests() -> None:
    @get("/cached/{value:str}", cache=True)
    def handler(value: FromPath[str]) -> str:
        return value

    with create_test_client([handler]) as client:
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"


async def test_middleware_does_not_leak_state_between_concurrent_requests() -> None:
    @get("/cached/{value:str}", cache=True)
    async def handler(value: FromPath[str]) -> str:
        return value

    results: dict[str, str] = {}

    async with create_async_test_client([handler]) as client:

        async def request(value: str) -> None:
            results[value] = (await client.get(f"/cached/{value}")).text

        async with anyio.create_task_group() as task_group:
            for value in ("first", "second", "third", "fourth"):
                task_group.start_soon(request, value)

    assert results == {"first": "first", "second": "second", "third": "third", "fourth": "fourth"}
