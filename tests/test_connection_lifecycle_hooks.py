from typing import Optional

import pytest

from starlite import (
    Controller,
    HTTPRouteHandler,
    Request,
    Response,
    Router,
    create_test_client,
    get,
)
from starlite.types import AfterRequestHandler, BeforeRequestHandler


def greet() -> dict:
    return {"hello": "world"}


def sync_before_request_handler_with_return_value(request: Request) -> dict:
    assert isinstance(request, Request)
    return {"hello": "moon"}


async def async_before_request_handler_with_return_value(request: Request) -> dict:
    assert isinstance(request, Request)
    return {"hello": "moon"}


def sync_before_request_handler_without_return_value(request: Request) -> None:
    assert isinstance(request, Request)
    return None


async def async_before_request_handler_without_return_value(request: Request) -> None:
    assert isinstance(request, Request)
    return None


def sync_after_request_handler(response: Response) -> Response:
    assert isinstance(response, Response)
    response.body = response.render({"hello": "moon"})
    return response


async def async_after_request_handler(response: Response) -> Response:
    assert isinstance(response, Response)
    response.body = response.render({"hello": "moon"})
    return response


@pytest.mark.parametrize(
    "handler, expected",
    [
        [get(path="/")(greet), {"hello": "world"}],
        [get(path="/", before_request=sync_before_request_handler_with_return_value)(greet), {"hello": "moon"}],
        [get(path="/", before_request=async_before_request_handler_with_return_value)(greet), {"hello": "moon"}],
        [get(path="/", before_request=sync_before_request_handler_without_return_value)(greet), {"hello": "world"}],
        [get(path="/", before_request=async_before_request_handler_without_return_value)(greet), {"hello": "world"}],
    ],
)
def test_before_request_handler_called(handler: HTTPRouteHandler, expected: dict) -> None:
    with create_test_client(route_handlers=handler) as client:
        response = client.get("/")
        assert response.json() == expected


@pytest.mark.parametrize(
    "handler, expected",
    [
        [get(path="/")(greet), {"hello": "world"}],
        [get(path="/", after_request=sync_after_request_handler)(greet), {"hello": "moon"}],
        [get(path="/", after_request=async_after_request_handler)(greet), {"hello": "moon"}],
    ],
)
def test_after_request_handler_called(handler: HTTPRouteHandler, expected: dict) -> None:
    with create_test_client(route_handlers=handler) as client:
        response = client.get("/")
        assert response.json() == expected


@pytest.mark.parametrize(
    "app_before_request_handler, router_before_request_handler, controller_before_request_handler, method_before_request_handler, expected",
    [
        [None, None, None, None, {"hello": "world"}],
        [sync_before_request_handler_with_return_value, None, None, None, {"hello": "moon"}],
        [None, sync_before_request_handler_with_return_value, None, None, {"hello": "moon"}],
        [None, None, sync_before_request_handler_with_return_value, None, {"hello": "moon"}],
        [None, None, None, sync_before_request_handler_with_return_value, {"hello": "moon"}],
        [
            sync_before_request_handler_with_return_value,
            async_before_request_handler_without_return_value,
            None,
            None,
            {"hello": "world"},
        ],
        [
            None,
            sync_before_request_handler_with_return_value,
            async_before_request_handler_without_return_value,
            None,
            {"hello": "world"},
        ],
        [
            None,
            None,
            sync_before_request_handler_with_return_value,
            async_before_request_handler_without_return_value,
            {"hello": "world"},
        ],
        [None, None, None, async_before_request_handler_without_return_value, {"hello": "world"}],
    ],
)
def test_before_request_handler_resolution(
    app_before_request_handler: Optional[BeforeRequestHandler],
    router_before_request_handler: Optional[BeforeRequestHandler],
    controller_before_request_handler: Optional[BeforeRequestHandler],
    method_before_request_handler: Optional[BeforeRequestHandler],
    expected: dict,
) -> None:
    class MyController(Controller):
        path = "/hello"

        before_request = controller_before_request_handler

        @get(before_request=method_before_request_handler)
        def hello(self) -> dict:
            return {"hello": "world"}

    router = Router(path="/greetings", route_handlers=[MyController], before_request=router_before_request_handler)

    with create_test_client(route_handlers=router, before_request=app_before_request_handler) as client:
        response = client.get("/greetings/hello")
        assert response.json() == expected


async def async_after_request_handler_with_hello_world(response: Response) -> Response:
    assert isinstance(response, Response)
    response.body = response.render({"hello": "world"})
    return response


@pytest.mark.parametrize(
    "app_after_request_handler, router_after_request_handler, controller_after_request_handler, method_after_request_handler, expected",
    [
        [None, None, None, None, {"hello": "world"}],
        [sync_after_request_handler, None, None, None, {"hello": "moon"}],
        [None, sync_after_request_handler, None, None, {"hello": "moon"}],
        [None, None, sync_after_request_handler, None, {"hello": "moon"}],
        [None, None, None, sync_after_request_handler, {"hello": "moon"}],
        [sync_after_request_handler, async_after_request_handler_with_hello_world, None, None, {"hello": "world"}],
        [None, sync_after_request_handler, async_after_request_handler_with_hello_world, None, {"hello": "world"}],
        [None, None, sync_after_request_handler, async_after_request_handler_with_hello_world, {"hello": "world"}],
        [None, None, None, async_after_request_handler_with_hello_world, {"hello": "world"}],
    ],
)
def test_after_request_handler_resolution(
    app_after_request_handler: Optional[AfterRequestHandler],
    router_after_request_handler: Optional[AfterRequestHandler],
    controller_after_request_handler: Optional[AfterRequestHandler],
    method_after_request_handler: Optional[AfterRequestHandler],
    expected: dict,
) -> None:
    class MyController(Controller):
        path = "/hello"

        after_request = controller_after_request_handler

        @get(after_request=method_after_request_handler)
        def hello(self) -> dict:
            return {"hello": "world"}

    router = Router(path="/greetings", route_handlers=[MyController], after_request=router_after_request_handler)

    with create_test_client(route_handlers=router, after_request=app_after_request_handler) as client:
        response = client.get("/greetings/hello")
        assert response.json() == expected
