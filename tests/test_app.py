import json
import logging

import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send

from starlite import (
    HTTPException,
    ImproperlyConfiguredException,
    MiddlewareProtocol,
    Request,
    Response,
    Starlite,
    create_test_client,
    get,
)
from starlite.datastructures import State


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
    assert len(unpacked_middleware) == 4


def test_lifecycle():
    counter = {"value": 0}

    def sync_function_without_state() -> None:
        counter["value"] += 1

    async def async_function_without_state() -> None:
        counter["value"] += 1

    def sync_function_with_state(state: State) -> None:
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.x = True

    async def async_function_with_state(state: State) -> None:
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.y = True

    with create_test_client(
        [],
        on_startup=[
            sync_function_without_state,
            async_function_without_state,
            sync_function_with_state,
            async_function_with_state,
        ],
        on_shutdown=[
            sync_function_without_state,
            async_function_without_state,
            sync_function_with_state,
            async_function_with_state,
        ],
    ) as client:
        assert counter["value"] == 4
        assert client.app.state.x
        assert client.app.state.y
        counter["value"] = 0
        assert counter["value"] == 0
    assert counter["value"] == 4


def test_register_validation_duplicate_handlers_for_same_route_and_method():
    @get(path="/first")
    def first_route_handler() -> None:
        pass

    @get(path="/first")
    def second_route_handler() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[first_route_handler, second_route_handler])
