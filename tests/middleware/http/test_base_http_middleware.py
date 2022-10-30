"""A parts of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/middleware/test_base.py. And are
meant to ensure our compatibility with their API.
"""

from typing import TYPE_CHECKING, Any

import pytest
from anyio import create_task_group, move_on_after

from starlite import (
    DefineMiddleware,
    Response,
    ValidationException,
    create_test_client,
    get,
)
from starlite.middleware.http import BaseHTTPMiddleware
from starlite.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from starlite import Request
    from starlite.middleware.http import CallNext
    from starlite.types import (
        ASGIApp,
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        Scope,
        Send,
    )


def test_custom_http_middleware() -> None:
    class SubclassMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            response = await call_next(request)
            response.headers["test"] = "123"
            return response

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.headers["test"] == "123"


def test_dispatch_raises_exception() -> None:
    class SubclassMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            raise ValidationException(detail="nope")

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_handler_raises_exception() -> None:
    class SubclassMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            return await call_next(request)

    @get("/")
    def handler() -> dict:
        raise ValidationException(detail="nope")

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_internal_server_exception_raised_if_no_response() -> None:
    class SubclassMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            return  # type: ignore

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR


def test_next_middleware_raises_exception() -> None:
    class SubclassMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            return await call_next(request)

    class ExceptionRaisingMiddleware:
        def __init__(self, app: "ASGIApp") -> None:
            self.app = app

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            raise ValidationException(detail="nope")

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(
        handler, middleware=[DefineMiddleware(SubclassMiddleware), DefineMiddleware(ExceptionRaisingMiddleware)]
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_state_data_across_multiple_middlewares() -> None:
    expected_value1 = "foo"
    expected_value2 = "bar"

    class aMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            request.state.foo = expected_value1
            return await call_next(request)

    class bMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            request.state.bar = expected_value2
            response = await call_next(request)
            response.headers["X-State-Foo"] = request.state.foo
            return response

    class cMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            response = await call_next(request)
            response.headers["X-State-Bar"] = request.state.bar
            return response

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(
        handler,
        middleware=[DefineMiddleware(aMiddleware), DefineMiddleware(bMiddleware), DefineMiddleware(cMiddleware)],
    ) as client:
        response = client.get("/")
        assert response.json() == {"hello": "world"}
        assert response.headers["X-State-Foo"] == expected_value1
        assert response.headers["X-State-Bar"] == expected_value2


def test_app_receives_http_disconnect_while_sending_if_discarded() -> None:
    class DiscardingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            await call_next(request)
            return Response(content={"hello": "world"})

    class RespondingMiddleware:
        def __init__(self, app: "ASGIApp") -> None:
            self.app = app

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            start_event: "HTTPResponseStartEvent" = {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain"),
                ],
            }

            await send(start_event)
            async with create_task_group() as task_group:

                async def cancel_on_disconnect() -> None:
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            task_group.cancel_scope.cancel()
                            break

                task_group.start_soon(cancel_on_disconnect)

                # A timeout is set for 0.1 second in order to ensure that
                # cancel_on_disconnect is scheduled by the event loop
                with move_on_after(0.1):
                    while True:
                        body_event: "HTTPResponseBodyEvent" = {
                            "type": "http.response.body",
                            "body": b"chunk ",
                            "more_body": True,
                        }
                        await send(body_event)

                pytest.fail("http.disconnect should have been received and canceled the scope")

    @get("/")
    def handler() -> None:
        return None

    with create_test_client(
        handler, middleware=[DefineMiddleware(DiscardingMiddleware), DefineMiddleware(RespondingMiddleware)]
    ) as client:
        response = client.get("/")
        assert response.json() == {"hello": "world"}


def test_app_receives_http_disconnect_after_sending_if_discarded() -> None:
    class DiscardingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: "Request[Any, Any]", call_next: "CallNext") -> Response[Any]:
            await call_next(request)
            return Response(content={"hello": "world"})

    @get("/")
    def handler() -> None:
        return None

    with create_test_client(handler, middleware=[DefineMiddleware(DiscardingMiddleware)]) as client:
        response = client.get("/")
        assert response.json() == {"hello": "world"}
