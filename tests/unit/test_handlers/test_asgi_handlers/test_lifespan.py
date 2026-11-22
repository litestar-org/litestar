import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.requests import Request as StarletteRequest
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from litestar import Litestar, Request, Router, asgi, get
from litestar.response.base import ASGIResponse
from litestar.testing import TestClient
from litestar.types import ASGIApp, LifeSpanReceive, LifeSpanReceiveMessage, LifeSpanScope, LifeSpanSend


def test_mounted_litestar_app_handles_request() -> None:
    @get("/")
    async def handler() -> str:
        return "mounted"

    mounted_app = Litestar([handler], openapi_config=None)
    app = Litestar([asgi("/sub", is_mount=True, lifespan=True)(mounted_app)], openapi_config=None)

    with TestClient(app) as client:
        assert client.get("/sub").text == "mounted"


async def test_without_lifespan_app_is_not_called() -> None:
    scopes: list[Any] = []

    @asgi("/sub", is_mount=True)
    async def mounted_app(scope: Any, receive: Any, send: Any) -> None:
        scopes.append(scope)

    async with Litestar([mounted_app], openapi_config=None).lifespan():
        pass

    assert scopes == []


async def test_lifespan_scope() -> None:
    scopes: list[Any] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        scopes.append(scope)
        await receive()
        await send({"type": "lifespan.startup.complete"})
        await receive()
        await send({"type": "lifespan.shutdown.complete"})

    async with Litestar([mounted_app], openapi_config=None).lifespan():
        pass

    assert scopes == [{"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}, "state": {}}]


def test_lifespan_state_in_request_scope() -> None:
    seen: list[Any] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen.append(scope["state"]["client"])
            await ASGIResponse()(scope, receive, send)

    with TestClient(Litestar([mounted_app], openapi_config=None)) as client:
        client.get("/sub")

    assert seen == ["client"]


def test_lifespan_state_of_starlette_app() -> None:
    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncGenerator[dict[str, Any], None]:
        yield {"client": "client"}

    async def index(request: StarletteRequest) -> PlainTextResponse:
        return PlainTextResponse(request.state.client)

    starlette_app = Starlette(routes=[Route("/", index)], lifespan=lifespan)
    app = Litestar([asgi("/sub", is_mount=True, lifespan=True)(starlette_app)], openapi_config=None)

    with TestClient(app) as client:
        assert client.get("/sub").text == "client"


def test_lifespan_state_per_handler() -> None:
    seen: list[Any] = []

    @asgi("/first", is_mount=True, lifespan=True)
    async def first_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client of first"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen.append(scope["state"]["client"])
            await ASGIResponse()(scope, receive, send)

    @asgi("/second", is_mount=True, lifespan=True)
    async def second_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client of second"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen.append(scope["state"]["client"])
            await ASGIResponse()(scope, receive, send)

    with TestClient(Litestar([first_app, second_app], openapi_config=None)) as client:
        client.get("/first")
        client.get("/second")

    assert seen == ["client of first", "client of second"]


def test_lifespan_state_not_in_request_scope_of_other_handler() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        scope["state"]["client"] = "client"
        await send({"type": "lifespan.startup.complete"})
        await receive()
        await send({"type": "lifespan.shutdown.complete"})

    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> bool:
        return "client" in request.scope["state"]

    with TestClient(Litestar([mounted_app, handler], openapi_config=None)) as client:
        assert client.get("/").json() is False


def test_lifespan_state_replaces_key_in_request_state() -> None:
    seen: list[Any] = []

    def middleware(app: ASGIApp) -> ASGIApp:
        async def middleware_app(scope: Any, receive: Any, send: Any) -> None:
            scope["state"]["client"] = "client of middleware"
            await app(scope, receive, send)

        return middleware_app

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen.append(scope["state"]["client"])
            await ASGIResponse()(scope, receive, send)

    with TestClient(Litestar([mounted_app], middleware=[middleware], openapi_config=None)) as client:
        client.get("/sub")

    assert seen == ["client"]


def test_lifespan_state_with_copy_state() -> None:
    seen_by_app: list[Any] = []
    seen_by_middleware: list[Any] = []

    def middleware(app: ASGIApp) -> ASGIApp:
        async def middleware_app(scope: Any, receive: Any, send: Any) -> None:
            await app(scope, receive, send)
            seen_by_middleware.append(scope["state"].get("client"))

        return middleware_app

    @asgi("/sub", is_mount=True, lifespan=True, copy_state=True)
    async def mounted_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen_by_app.append(scope["state"]["client"])
            await ASGIResponse()(scope, receive, send)

    with TestClient(Litestar([mounted_app], middleware=[middleware], openapi_config=None)) as client:
        client.get("/sub")

    assert seen_by_app == ["client"]
    assert seen_by_middleware == [None]


def test_lifespan_state_set_in_request_not_kept() -> None:
    seen: list[Any] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await receive()
            scope["state"]["client"] = "client"
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})
        else:
            seen.append(scope["state"]["client"])
            scope["state"]["client"] = "client set in request"
            await ASGIResponse()(scope, receive, send)

    with TestClient(Litestar([mounted_app], openapi_config=None)) as client:
        client.get("/sub")
        client.get("/sub")

    assert seen == ["client", "client"]


async def test_second_lifespan_starts_with_empty_state() -> None:
    states_at_startup: list[dict[str, Any]] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        states_at_startup.append(dict(scope["state"]))
        scope["state"]["client"] = "client"
        await send({"type": "lifespan.startup.complete"})
        await receive()
        await send({"type": "lifespan.shutdown.complete"})

    app = Litestar([mounted_app], openapi_config=None)

    async with app.lifespan():
        pass
    async with app.lifespan():
        pass

    assert states_at_startup == [{}, {}]


async def test_lifespan_order() -> None:
    events: list[str] = []
    dependency_context_open: list[bool] = []

    @asynccontextmanager
    async def manager(_: Litestar) -> AsyncGenerator[None, None]:
        events.append("manager enter")
        yield
        events.append("manager exit")

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        events.append("mounted startup")
        dependency_context_open.append(app.dependency_context is not None)
        await send({"type": "lifespan.startup.complete"})
        await receive()
        events.append("mounted shutdown")
        dependency_context_open.append(app.dependency_context is not None)
        await send({"type": "lifespan.shutdown.complete"})

    app = Litestar(
        [mounted_app],
        lifespan=[manager],
        on_startup=[lambda: events.append("on_startup")],
        on_shutdown=[lambda: events.append("on_shutdown")],
        openapi_config=None,
    )

    async with app.lifespan():
        events.append("running")

    assert events == [
        "manager enter",
        "on_startup",
        "mounted startup",
        "running",
        "mounted shutdown",
        "manager exit",
        "on_shutdown",
    ]
    assert dependency_context_open == [True, True]


async def test_handler_with_two_paths_runs_lifespan_once() -> None:
    received: list[LifeSpanReceiveMessage] = []

    @asgi(["/a", "/b"], is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        received.append(await receive())
        await send({"type": "lifespan.startup.complete"})
        received.append(await receive())
        await send({"type": "lifespan.shutdown.complete"})

    async with Litestar([mounted_app], openapi_config=None).lifespan():
        pass

    assert received == [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]


async def test_lifespan_of_handler_on_router() -> None:
    received: list[LifeSpanReceiveMessage] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        received.append(await receive())
        await send({"type": "lifespan.startup.complete"})
        received.append(await receive())
        await send({"type": "lifespan.shutdown.complete"})

    async with Litestar([Router("/router", route_handlers=[mounted_app])], openapi_config=None).lifespan():
        pass

    assert received == [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]


async def test_app_shut_down_when_lifespan_body_raises() -> None:
    received: list[LifeSpanReceiveMessage] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        received.append(await receive())
        await send({"type": "lifespan.startup.complete"})
        received.append(await receive())
        await send({"type": "lifespan.shutdown.complete"})

    with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="body failed")):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            raise ValueError("body failed")

    assert received == [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]


async def test_app_raising_on_startup_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        raise ValueError("cannot handle lifespan")

    with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="cannot handle lifespan")):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_app_raising_after_startup_failed_event_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.startup.failed", "message": "traceback"})
        raise ValueError("database unreachable")

    with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="database unreachable")):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_startup_failed_event_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.startup.failed", "message": "database unreachable"})

    with pytest.RaisesGroup(
        pytest.RaisesExc(
            RuntimeError,
            match=r"\[paths='/sub', handler='.*mounted_app'\] on 'lifespan.startup' the ASGI app sent "
            r"'lifespan.startup.failed': database unreachable",
        )
    ):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_app_waiting_after_startup_failed_event_is_cancelled() -> None:
    received: list[LifeSpanReceiveMessage] = []
    cancelled: list[bool] = []

    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        received.append(await receive())
        await send({"type": "lifespan.startup.failed", "message": "database unreachable"})
        try:
            received.append(await receive())
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    with pytest.RaisesGroup(pytest.RaisesExc(RuntimeError, match="sent 'lifespan.startup.failed'")):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass

    assert received == [{"type": "lifespan.startup"}]
    assert cancelled == [True]


async def test_app_returning_before_startup_complete_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        return

    with pytest.RaisesGroup(
        pytest.RaisesExc(
            RuntimeError,
            match=r"\[paths='/sub', handler='.*mounted_app'\] on 'lifespan.startup' the ASGI app returned without "
            r"sending 'lifespan.startup.complete'",
        )
    ):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_unexpected_message_on_startup_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.shutdown.complete"})

    with pytest.RaisesGroup(
        pytest.RaisesExc(
            RuntimeError,
            match=r"\[paths='/sub', handler='.*mounted_app'\] on 'lifespan.startup' the ASGI app sent "
            r"'lifespan.shutdown.complete'$",
        )
    ):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_app_raising_on_shutdown_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.startup.complete"})
        await receive()
        raise ValueError("connections left open")

    with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="connections left open")):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_shutdown_failed_event_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.startup.complete"})
        await receive()
        await send({"type": "lifespan.shutdown.failed", "message": "connections left open"})

    with pytest.RaisesGroup(
        pytest.RaisesExc(
            RuntimeError,
            match=r"\[paths='/sub', handler='.*mounted_app'\] on 'lifespan.shutdown' the ASGI app sent "
            r"'lifespan.shutdown.failed': connections left open",
        )
    ):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass


async def test_app_returning_before_shutdown_complete_raises() -> None:
    @asgi("/sub", is_mount=True, lifespan=True)
    async def mounted_app(scope: LifeSpanScope, receive: LifeSpanReceive, send: LifeSpanSend) -> None:
        await receive()
        await send({"type": "lifespan.startup.complete"})

    with pytest.RaisesGroup(
        pytest.RaisesExc(
            RuntimeError,
            match=r"\[paths='/sub', handler='.*mounted_app'\] on 'lifespan.shutdown' the ASGI app returned without "
            r"sending 'lifespan.shutdown.complete'",
        )
    ):
        async with Litestar([mounted_app], openapi_config=None).lifespan():
            pass
