from functools import partial
from typing import Any, Awaitable, Callable

import pytest
from anyio.to_thread import run_sync

from starlite import Controller, HTTPRouteHandler, Router, Starlite
from starlite.lifecycle_hooks import LifecycleHook


@pytest.fixture()
def sync_callable() -> Callable[[str], str]:
    def f(s: str) -> str:
        return f"sync callable: {s}"

    return f


@pytest.fixture()
def sync_hook(sync_callable: Callable[[str], str]) -> LifecycleHook:
    return LifecycleHook(sync_callable)


@pytest.fixture()
def async_callable() -> Callable[[str], Awaitable[str]]:
    async def f(s: str) -> str:
        return f"async callable: {s}"

    return f


@pytest.fixture()
def async_hook(async_callable: Callable[[str], Awaitable[str]]) -> LifecycleHook:
    return LifecycleHook(async_callable)


def test_init_lifecycle_handler_sync_callable(sync_callable: Callable[[str], str], sync_hook: LifecycleHook) -> None:
    assert isinstance(sync_hook.handler, partial)
    assert sync_hook.handler.func is run_sync  # type:ignore[unreachable]
    assert sync_hook.handler.args == (sync_callable,)


def test_init_lifecycle_handler_async_callable(
    async_callable: Callable[[str], Awaitable[str]], async_hook: LifecycleHook
) -> None:
    assert async_hook.handler is async_callable


async def test_call_sync_hook(sync_hook: LifecycleHook) -> None:
    assert await sync_hook("called") == "sync callable: called"


async def test_call_async_hook(async_hook: LifecycleHook) -> None:
    assert await async_hook("called") == "async callable: called"


def test_layer_lifecycle_hook_handler_attribute_assignment() -> None:
    """
    Test ensures behavior of both functions and instance methods passed as lifecycle hook handlers to the layer type
    constructors, after the handlers have been assigned to an attribute on the layer type instance.
    """

    class HandlerClass:
        def handler_method(self, _: Any) -> Any:
            return f"{type(self).__name__}: method all good"

    def handler_func(_: Any) -> Any:
        return "func all good"

    handler_method = HandlerClass().handler_method
    app = Starlite(route_handlers=[], before_request=handler_func, after_request=handler_method)
    router = Router(path="", route_handlers=[], before_request=handler_func, after_request=handler_method)
    route_handler = HTTPRouteHandler(http_method="GET", before_request=handler_func, after_request=handler_method)

    for layer in (app, router, route_handler):
        assert getattr(layer, "before_request")(None) == "func all good"
        assert getattr(layer, "after_request")(None) == "HandlerClass: method all good"


def test_controller_lifecycle_hook_handler_attribute_assignment() -> None:
    """
    Test ensures consistent behavior to that of the other layer types when lifecycle hook handlers are associated with
    a `Controller` instance via assignment to class variable.
    """

    class HandlerClass:
        def handler_method(self, _: Any) -> Any:
            # includes class name to verify that `self` is not reassigned to `TestController` on instantiation
            return f"{type(self).__name__}: method all good"

    handler_instance = HandlerClass()

    def handler_func(_: Any) -> Any:
        return "func all good"

    class TestController(Controller):
        path = ""
        before_request = handler_func
        after_request = handler_instance.handler_method

    controller = TestController(owner=Router(path="", route_handlers=[]))

    assert getattr(controller, "before_request")(None) == "func all good"
    assert getattr(controller, "after_request")(None) == "HandlerClass: method all good"
