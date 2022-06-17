import logging
from typing import Any, Awaitable, Callable

import pytest
from _pytest.logging import LogCaptureFixture
from pydantic import BaseModel
from pytest_mock import MockerFixture
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from starlite import (
    CORSConfig,
    MiddlewareProtocol,
    Request,
    Response,
    Starlite,
    create_test_client,
    get,
    post,
)

logger = logging.getLogger(__name__)


class MiddlewareProtocolRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:

        if scope["type"] == "http":
            request: Request = Request(scope=scope, receive=receive)
            body = await request.json()
            logger.info(f"test logging: {request.method}, {request.url}, {body}")
        await self.app(scope, receive, send)


class BaseMiddlewareRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # type: ignore[override]
        logger = logging.getLogger(__name__)
        logger.info("%s - %s", request.method, request.url)
        return await call_next(request)  # type: ignore


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, header_value: str = "Example") -> None:
        super().__init__(app)
        self.header_value = header_value

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        response = await call_next(request)
        response.headers["Custom"] = self.header_value
        return response


@pytest.mark.parametrize(
    "middleware",
    [
        MiddlewareProtocolRequestLoggingMiddleware,
        BaseMiddlewareRequestLoggingMiddleware,
        Middleware(CustomHeaderMiddleware, header_value="Customized"),
    ],
)
def test_custom_middleware_processing(middleware: Any) -> None:
    app = Starlite(route_handlers=[], middleware=[middleware])
    unpacked_middleware = []
    cur = app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app  # type: ignore
    assert len(unpacked_middleware) == 2


@get(path="/")
def handler() -> None:
    ...


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

    client = create_test_client(route_handlers=[handler], cors_config=cors_config)
    unpacked_middleware = []
    cur = client.app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app  # type: ignore
    assert len(unpacked_middleware) == 2
    cors_middleware = unpacked_middleware[0]
    assert isinstance(cors_middleware, CORSMiddleware)
    assert cors_middleware.allow_headers == ["*", "accept", "accept-language", "content-language", "content-type"]
    assert cors_middleware.allow_methods == ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
    assert cors_middleware.allow_origins == cors_config.allow_origins
    assert cors_middleware.allow_origin_regex == cors_config.allow_origin_regex


def test_trusted_hosts_middleware() -> None:
    client = create_test_client(route_handlers=[handler], allowed_hosts=["*"])
    unpacked_middleware = []
    cur = client.app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app  # type: ignore
    assert len(unpacked_middleware) == 2
    trusted_hosts_middleware = unpacked_middleware[0]
    assert isinstance(trusted_hosts_middleware, TrustedHostMiddleware)
    assert trusted_hosts_middleware.allowed_hosts == ["*"]


def test_request_body_logging_middleware(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        client = create_test_client(
            route_handlers=[post_handler], middleware=[MiddlewareProtocolRequestLoggingMiddleware]
        )
        response = client.post("/", json={"name": "moishe zuchmir", "age": 40, "programmer": True})
        assert response.status_code == 201
        assert "test logging" in caplog.text


def test_middleware_call_order(mocker: MockerFixture) -> None:
    """Test that middlewares are called in the order they have been passed"""
    m1 = mocker.spy(BaseMiddlewareRequestLoggingMiddleware, "dispatch")
    m2 = mocker.spy(CustomHeaderMiddleware, "dispatch")
    manager = mocker.Mock()
    manager.attach_mock(m1, "m1")
    manager.attach_mock(m2, "m2")

    client = create_test_client(
        route_handlers=[handler],
        middleware=[
            BaseMiddlewareRequestLoggingMiddleware,
            Middleware(CustomHeaderMiddleware, header_value="Customized"),
        ],
    )
    client.get("/")

    manager.assert_has_calls([mocker.call.m1(*m1.call_args[0]), mocker.call.m2(*m2.call_args[0])], any_order=False)
