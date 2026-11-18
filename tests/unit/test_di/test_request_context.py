from collections.abc import AsyncGenerator
from typing import Any

import pytest

from litestar import Litestar, Request, WebSocket, asgi, get, websocket
from litestar.background_tasks import BackgroundTask
from litestar.connection import ASGIConnection
from litestar.di import DIContext, NamedDependency, Provider
from litestar.exceptions import LitestarException
from litestar.response import Response, Stream
from litestar.testing import TestClient
from litestar.types import ASGIApp, Empty, Message, Receive, ReceiveMessage, Scope, Send
from litestar.utils.scope.state import ScopeState


def _http_scope(path: str = "/") -> Scope:
    return {  # type: ignore[return-value]
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }


def test_request_context_spans_middleware_guards_handler_background_tasks_and_after_response() -> None:
    seen: dict[str, tuple[DIContext, bool]] = {}

    def record(where: str, scope: Scope) -> None:
        context = ScopeState.from_scope(scope).dependency_context
        assert context is not Empty
        seen[where] = (context, context.closed)

    def middleware(app: ASGIApp) -> ASGIApp:
        async def middleware_app(scope: Scope, receive: Receive, send: Send) -> None:
            record("middleware", scope)
            await app(scope, receive, send)

        return middleware_app

    async def guard(connection: ASGIConnection, _: Any) -> None:
        record("guard", connection.scope)

    async def after_response(request: Request) -> None:
        record("after response", request.scope)

    @get("/", middleware=[middleware], guards=[guard], after_response=after_response)
    async def handler(request: Request) -> Response[None]:
        record("handler", request.scope)
        return Response(None, background=BackgroundTask(record, "background task", request.scope))

    app = Litestar([handler], openapi_config=None)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        app_context = app._dependency_context

    context = seen["handler"][0]
    assert seen == dict.fromkeys(
        ("middleware", "guard", "handler", "background task", "after response"), (context, False)
    )
    assert context.closed
    assert context.scope == "request"
    assert context.parent is app_context
    assert context.registry is app.route_handler_method_map["/"]["GET"]._injection_setup.registry


def test_websocket_request_context_spans_handler() -> None:
    seen: dict[str, Any] = {}

    @websocket("/")
    async def handler(socket: WebSocket) -> None:
        context = ScopeState.from_scope(socket.scope).dependency_context
        assert context is not Empty
        seen["context"], seen["closed in handler"] = context, context.closed
        await socket.accept()
        await socket.close()

    app = Litestar([handler], openapi_config=None)
    with TestClient(app) as client, client.websocket_connect("/"):
        pass

    assert seen["closed in handler"] is False
    assert seen["context"].closed
    assert seen["context"].scope == "request"
    assert seen["context"].registry is app.route_handler_method_map["/"]["websocket"]._injection_setup.registry


async def test_http_request_without_lifespan_raises() -> None:
    @get("/")
    async def handler() -> None: ...

    async def receive() -> ReceiveMessage:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None: ...

    app = Litestar([handler], openapi_config=None)

    with pytest.raises(
        RuntimeError, match="^Cannot handle the request to '/': the lifespan of the app is not running$"
    ):
        await app(_http_scope(), receive, send)


async def test_websocket_without_lifespan_raises() -> None:
    @websocket("/")
    async def handler(socket: WebSocket) -> None: ...

    async def receive() -> ReceiveMessage:
        return {"type": "websocket.connect"}

    async def send(message: Message) -> None: ...

    scope = {**_http_scope(), "type": "websocket", "scheme": "ws", "subprotocols": []}
    del scope["method"]
    app = Litestar([handler], openapi_config=None)

    with pytest.raises(
        RuntimeError, match="^Cannot handle the request to '/': the lifespan of the app is not running$"
    ):
        await app(scope, receive, send)  # type: ignore[arg-type]


async def test_http_request_without_app_scope_and_lifespan() -> None:
    messages: list[Message] = []

    @get("/")
    async def handler() -> str:
        return "ok"

    async def receive() -> ReceiveMessage:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    app = Litestar([handler], openapi_config=None, dependency_scopes=("request", "handler"))
    await app(_http_scope(), receive, send)

    assert messages[0]["status"] == 200  # type: ignore[typeddict-item]
    assert messages[1]["body"] == b"ok"  # type: ignore[typeddict-item]


async def test_websocket_without_app_scope_and_lifespan() -> None:
    messages: list[Message] = []

    @websocket("/")
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.close()

    async def receive() -> ReceiveMessage:
        return {"type": "websocket.connect"}

    async def send(message: Message) -> None:
        messages.append(message)

    scope = {**_http_scope(), "type": "websocket", "scheme": "ws", "subprotocols": []}
    del scope["method"]
    app = Litestar([handler], openapi_config=None, dependency_scopes=("request", "handler"))
    await app(scope, receive, send)  # type: ignore[arg-type]

    assert [message["type"] for message in messages] == ["websocket.accept", "websocket.close"]


def test_lifespan_without_app_scope() -> None:
    started: list[bool] = []

    async def on_startup() -> None:
        started.append(True)

    @get("/")
    async def handler() -> str:
        return "ok"

    app = Litestar([handler], on_startup=[on_startup], openapi_config=None, dependency_scopes=("request", "handler"))

    with TestClient(app) as client:
        assert client.get("/").text == "ok"
    assert started == [True]


@pytest.mark.parametrize("is_mount", [False, True])
async def test_asgi_route_without_lifespan_has_no_request_context(is_mount: bool) -> None:
    seen: list[Any] = []
    messages: list[Message] = []

    @asgi("/", is_mount=is_mount)
    async def handler(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(ScopeState.from_scope(scope).dependency_context)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def receive() -> ReceiveMessage:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    await Litestar([handler], openapi_config=None)(_http_scope(), receive, send)

    assert seen == [Empty]
    assert messages[0] == {"type": "http.response.start", "status": 200, "headers": []}


def test_mounted_litestar_app_without_its_lifespan_answers_500() -> None:
    @get("/")
    async def handler() -> str:
        return "mounted"

    mounted_app = Litestar([handler], openapi_config=None)
    app = Litestar([asgi("/sub", is_mount=True)(mounted_app)], openapi_config=None)

    with TestClient(app) as client:
        assert client.get("/sub").status_code == 500


def test_mounted_litestar_app_with_its_lifespan_run_by_outer_app_handles_request() -> None:
    @get("/")
    async def handler() -> str:
        return "mounted"

    mounted_app = Litestar([handler], openapi_config=None)
    app = Litestar(
        [asgi("/sub", is_mount=True)(mounted_app)],
        lifespan=[lambda _: mounted_app.lifespan()],
        openapi_config=None,
    )

    with TestClient(app) as client:
        assert client.get("/sub").text == "mounted"


def _passthrough_middleware(app: ASGIApp) -> ASGIApp:
    async def middleware_app(scope: Scope, receive: Receive, send: Send) -> None:
        await app(scope, receive, send)

    return middleware_app


@pytest.mark.parametrize("middleware", [[], [_passthrough_middleware]], ids=["no middleware", "route middleware"])
def test_request_scoped_generator_torn_down_after_response(middleware: list[Any]) -> None:
    events: list[str] = []

    async def provide_value() -> AsyncGenerator[int, None]:
        yield 1
        events.append("teardown")

    async def after_response(request: Request) -> None:
        events.append("after response")

    @get("/", middleware=middleware, after_response=after_response)
    async def handler(value: NamedDependency[int]) -> int:
        return value

    app = Litestar([handler], dependencies=[Provider(provide_value, key="value", scope="request")], openapi_config=None)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200

    assert events == ["after response", "teardown"]


@pytest.mark.parametrize("middleware", [[], [_passthrough_middleware]], ids=["no middleware", "route middleware"])
def test_exception_handled_by_exception_handler_not_thrown_into_request_scoped_generator(middleware: list[Any]) -> None:
    thrown: list[BaseException | None] = []

    async def provide_value() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except BaseException as exc:
            thrown.append(exc)
            raise
        thrown.append(None)

    def handle_value_error(request: Request, exc: ValueError) -> Response[str]:
        return Response("handled", status_code=400)

    @get("/", middleware=middleware)
    async def handler(value: NamedDependency[int]) -> int:
        raise ValueError

    app = Litestar(
        [handler],
        dependencies=[Provider(provide_value, key="value", scope="request")],
        exception_handlers={ValueError: handle_value_error},
        openapi_config=None,
    )
    with TestClient(app) as client:
        assert client.get("/").status_code == 400

    assert thrown == [None]


@pytest.mark.parametrize("middleware", [[], [_passthrough_middleware]], ids=["no middleware", "route middleware"])
def test_exception_without_exception_handler_thrown_into_request_scoped_generator(middleware: list[Any]) -> None:
    thrown: list[BaseException | None] = []
    error = ValueError()

    async def provide_value() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except BaseException as exc:
            thrown.append(exc)
            raise
        thrown.append(None)

    @get("/", middleware=middleware)
    async def handler(value: NamedDependency[int]) -> int:
        raise error

    app = Litestar([handler], dependencies=[Provider(provide_value, key="value", scope="request")], openapi_config=None)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/").status_code == 500

    assert thrown == [error]


@pytest.mark.parametrize("middleware", [[], [_passthrough_middleware]], ids=["no middleware", "route middleware"])
def test_exception_raised_after_response_started_thrown_into_request_scoped_generator(middleware: list[Any]) -> None:
    thrown: list[BaseException | None] = []

    async def provide_value() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except BaseException as exc:
            thrown.append(exc)
            raise
        thrown.append(None)

    @get("/", middleware=middleware)
    async def handler(value: NamedDependency[int]) -> Stream:
        async def iterator() -> AsyncGenerator[bytes, None]:
            yield b"a"
            raise ValueError

        return Stream(iterator())

    app = Litestar([handler], dependencies=[Provider(provide_value, key="value", scope="request")], openapi_config=None)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/")

    assert len(thrown) == 1
    assert isinstance(thrown[0], LitestarException)
    assert thrown[0].detail == "Exception caught after response started"


def test_exception_raised_by_route_middleware_thrown_into_request_scoped_generator() -> None:
    thrown: list[BaseException | None] = []
    error = ValueError()

    async def provide_value() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except BaseException as exc:
            thrown.append(exc)
            raise
        thrown.append(None)

    def middleware(app: ASGIApp) -> ASGIApp:
        async def middleware_app(scope: Scope, receive: Receive, send: Send) -> None:
            await app(scope, receive, send)
            raise error

        return middleware_app

    @get("/", middleware=[middleware])
    async def handler(value: NamedDependency[int]) -> int:
        return value

    app = Litestar([handler], dependencies=[Provider(provide_value, key="value", scope="request")], openapi_config=None)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/")

    assert thrown == [error]
