import json
import logging

import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send

from starlite import HTTPException, MiddlewareProtocol, Request, Response, Starlite


def test_handle_http_exception():
    response = Starlite.handle_http_exception("", HTTPException(detail="starlite_exception", extra={"key": "value"}))
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
    }

    response = Starlite.handle_http_exception(
        "", StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
    }

    response = Starlite.handle_http_exception("", AttributeError("oops"))
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
    }


class MiddlewareProtocolRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        logger = logging.getLogger(__name__)
        if scope["type"] == "http":
            request = Request(scope)
            logger.info("%s - %s", request.method, request.url)
        await self.app(scope, receive, send)


class BaseMiddlewareRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        logger = logging.getLogger(__name__)
        logger.info("%s - %s", request.method, request.url)
        return await call_next(request)


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_value="Example"):
        super().__init__(app)
        self.header_value = header_value

    async def dispatch(self, request, call_next):
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
def test_middleware_processing(middleware):
    app = Starlite(route_handlers=[], middleware=[middleware])
    unpacked_middleware = []
    cur = app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app
    assert len(unpacked_middleware) == 3
