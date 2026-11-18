import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from litestar import Litestar, get
from litestar.di.exceptions import DIScopeError
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.types import Message, ReceiveMessage


async def test_app_context_entered_after_lifespan_managers_and_closed_before_them() -> None:
    seen: dict[str, Any] = {}

    @asynccontextmanager
    async def manager(app: Litestar) -> AsyncGenerator[None, None]:
        seen["context at manager entry"] = app._dependency_context
        yield
        seen["context closed at manager exit"] = seen["context at startup"].closed

    def on_startup(app: Litestar) -> None:
        seen["context at startup"] = app._dependency_context

    app = Litestar(lifespan=[manager], on_startup=[on_startup], openapi_config=None)

    async with app.lifespan():
        assert await seen["context at startup"].solve(Litestar) is app

    assert seen["context at manager entry"] is None
    assert seen["context closed at manager exit"] is True
    assert app._dependency_context is None


async def test_app_context_of_app_subclass_holds_app_under_both_classes() -> None:
    class App(Litestar):
        pass

    app = App(openapi_config=None)

    async with app.lifespan():
        assert app._dependency_context is not None
        assert await app._dependency_context.solve(Litestar) is app
        assert await app._dependency_context.solve(App) is app


async def test_concurrent_second_lifespan_raises() -> None:
    startups: list[None] = []
    app = Litestar(on_startup=[lambda: startups.append(None)], openapi_config=None)

    async with app.lifespan():
        context = app._dependency_context
        with pytest.raises(RuntimeError, match="is already running"):
            async with app.lifespan():
                pass

        assert app._dependency_context is context
    assert len(startups) == 1


async def test_lifespan_after_lifespan_enters_new_app_context() -> None:
    app = Litestar(openapi_config=None)

    async with app.lifespan():
        first = app._dependency_context
    async with app.lifespan():
        second = app._dependency_context
        assert second is not None
        assert not second.closed

    assert first is not None
    assert first.closed
    assert second is not first


async def test_register_while_lifespan_running_raises() -> None:
    @get("/late")
    async def late() -> None: ...

    app = Litestar(openapi_config=None)

    async with app.lifespan():
        with pytest.raises(ImproperlyConfiguredException, match="while the lifespan of .* is running"):
            app.register(late)


async def test_shutdown_with_open_request_context_raises() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    @get("/")
    async def handler() -> None:
        started.set()
        await release.wait()

    async def receive() -> ReceiveMessage:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None: ...

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    app = Litestar([handler], openapi_config=None)
    lifespan = app.lifespan()
    await lifespan.__aenter__()
    request = asyncio.create_task(app(scope, receive, send))  # type: ignore[arg-type]
    await started.wait()

    with pytest.RaisesGroup(pytest.RaisesExc(DIScopeError, match="was closed while 1 nested context")):
        await lifespan.__aexit__(None, None, None)

    release.set()
    with pytest.raises(LitestarException, match="Exception caught after response started"):
        await request
