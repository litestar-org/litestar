import logging
import secrets
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, cast

import pytest
from pydantic import BaseModel
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from starlite import (
    Controller,
    CORSConfig,
    DefineMiddleware,
    MiddlewareProtocol,
    Request,
    Response,
    Router,
    get,
    post,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from typing import Type

    from _pytest.logging import LogCaptureFixture
    from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class MiddlewareProtocolRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", kwarg: str = "") -> None:
        super().__init__(app)
        self.app = app
        self.kwarg = kwarg

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] == "http":
            request: Request = Request(scope=scope, receive=receive)
            body = await request.json()
            logger.info(f"test logging: {request.method}, {request.url}, {body}")
        await self.app(scope, receive, send)


class BaseMiddlewareRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # type: ignore
        logging.getLogger(__name__).info("%s - %s", request.method, request.url)
        return await call_next(request)  # type: ignore


class MiddlewareWithArgsAndKwargs(BaseHTTPMiddleware):
    def __init__(self, arg: int = 0, *, app: Any, kwarg: str) -> None:
        super().__init__(app)
        self.arg = arg
        self.kwarg = kwarg

    async def dispatch(  # type: ignore
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ...


@get(path="/")
def handler() -> None:
    ...


@pytest.mark.parametrize(
    "middleware",
    [
        BaseMiddlewareRequestLoggingMiddleware,
        Middleware(MiddlewareWithArgsAndKwargs, kwarg="123Jeronimo"),
        Middleware(MiddlewareProtocolRequestLoggingMiddleware, kwarg="123Jeronimo"),
        DefineMiddleware(MiddlewareWithArgsAndKwargs, 1, kwarg="123Jeronimo"),
        DefineMiddleware(MiddlewareProtocolRequestLoggingMiddleware, kwarg="123Jeronimo"),
    ],
)
def test_custom_middleware_processing(middleware: Any) -> None:
    with create_test_client(route_handlers=[handler], middleware=[middleware]) as client:
        app = client.app
        assert app.middleware == [middleware]

        unpacked_middleware = []
        cur = client.app.route_map["/"]["_asgi_handlers"]["GET"]
        while hasattr(cur, "app"):
            unpacked_middleware.append(cur)
            cur = cast("ASGIApp", cur.app)
        else:
            unpacked_middleware.append(cur)
        assert len(unpacked_middleware) == 4

        middleware_instance = unpacked_middleware[1]

        assert isinstance(
            middleware_instance,
            (
                MiddlewareProtocolRequestLoggingMiddleware,
                BaseMiddlewareRequestLoggingMiddleware,
                MiddlewareWithArgsAndKwargs,
            ),
        )
        if isinstance(middleware_instance, (MiddlewareProtocolRequestLoggingMiddleware, MiddlewareWithArgsAndKwargs)):
            assert middleware_instance.kwarg == "123Jeronimo"
        if isinstance(middleware, DefineMiddleware) and isinstance(middleware_instance, MiddlewareWithArgsAndKwargs):
            assert middleware_instance.arg == 1


class JSONRequest(BaseModel):
    name: str
    age: int
    programmer: bool


@post(path="/")
def post_handler(data: JSONRequest) -> JSONRequest:
    return data


def test_setting_cors_middleware() -> None:
    cors_config = CORSConfig()
    assert cors_config.allow_credentials is False
    assert cors_config.allow_headers == ["*"]
    assert cors_config.allow_methods == ["*"]
    assert cors_config.allow_origins == ["*"]
    assert cors_config.allow_origin_regex is None
    assert cors_config.max_age == 600
    assert cors_config.expose_headers == []

    with create_test_client(route_handlers=[handler], cors_config=cors_config) as client:
        unpacked_middleware = []
        cur = client.app.asgi_handler
        while hasattr(cur, "app"):
            unpacked_middleware.append(cur)
            cur = cast("ASGIApp", cur.app)  # type: ignore
        else:
            unpacked_middleware.append(cur)
        assert len(unpacked_middleware) == 4
        cors_middleware = unpacked_middleware[1]
        assert isinstance(cors_middleware, CORSMiddleware)
        assert cors_middleware.allow_headers == ["*", "accept", "accept-language", "content-language", "content-type"]
        assert cors_middleware.allow_methods == ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
        assert cors_middleware.allow_origins == cors_config.allow_origins
        assert cors_middleware.allow_origin_regex == cors_config.allow_origin_regex


def test_trusted_hosts_middleware() -> None:
    client = create_test_client(route_handlers=[handler], allowed_hosts=["*"])
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 4
    trusted_hosts_middleware = unpacked_middleware[1]
    assert isinstance(trusted_hosts_middleware, TrustedHostMiddleware)
    assert trusted_hosts_middleware.allowed_hosts == ["*"]


def test_request_body_logging_middleware(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO):
        client = create_test_client(
            route_handlers=[post_handler], middleware=[MiddlewareProtocolRequestLoggingMiddleware]
        )
        response = client.post("/", json={"name": "moishe zuchmir", "age": 40, "programmer": True})
        assert response.status_code == 201
        assert "test logging" in caplog.text


def test_middleware_call_order() -> None:
    """Test that middlewares are called in the order they have been passed."""

    results: List[int] = []

    def create_test_middleware(middleware_id: int) -> "Type[MiddlewareProtocol]":
        class TestMiddleware(MiddlewareProtocol):
            def __init__(self, app: "ASGIApp"):
                self.app = app

            async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
                results.append(middleware_id)
                await self.app(scope, receive, send)

        return TestMiddleware

    class MyController(Controller):
        path = "/controller"
        middleware = [create_test_middleware(4), create_test_middleware(5)]

        @get("/handler", middleware=[create_test_middleware(6), create_test_middleware(7)])
        def my_handler(self) -> None:
            return None

    router = Router(
        path="/router", route_handlers=[MyController], middleware=[create_test_middleware(2), create_test_middleware(3)]
    )

    with create_test_client(
        route_handlers=[router],
        middleware=[create_test_middleware(0), create_test_middleware(1)],
    ) as client:
        client.get("/router/controller/handler")

        assert results == [0, 1, 2, 3, 4, 5, 6, 7]


@pytest.mark.xfail(reason="Cannot set cookie of size greater than the allowed max-size.", strict=True)
def test_session_middleware_should_fail_setcookie() -> None:
    """Test if size of set cookie is greater than max-size limit of cookie
    allowed by the browsers."""

    @get("/session")
    def session_handler(request: Request) -> None:
        """Mock route handler to set session."""
        # Fill the session with large string to exceed the max-size limit.
        request.session["mock_cookie"] = secrets.token_hex(1514)

    client = create_test_client(
        route_handlers=[session_handler],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key=secrets.token_hex(16))],
    )
    response = client.get("/session")
    assert response.status_code == 200
    assert len(response.cookies["session"]) < 4096
