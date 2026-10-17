from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from litestar import Litestar, get, post, websocket_listener
from litestar._asgi.routing_trie.mapping import build_route_middleware_stack
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware
from litestar.params import FromPath
from litestar.routes import HTTPRoute
from litestar.testing import create_test_client


def test_build_route_middleware_stack_no_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    # if there is no middleware for the route, then we don't need to wrap route.handle in
    # exception handling middleware. Exceptions can safely be caught by the outermost exception
    # handling middleware.

    @get("/")
    async def handler() -> None:
        pass

    app = Litestar(route_handlers=[handler], openapi_config=None)
    route = app.routes[0]
    handle_mock = MagicMock()
    monkeypatch.setattr(type(route), "handle", handle_mock)
    asgi_app = build_route_middleware_stack(app=app, route=route, route_handler=handler)
    assert asgi_app is handle_mock


def test_build_route_middleware_stack_with_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    # proves that if there is middleware, the route handler is wrapped in the exception handling
    # middleware, before being wrapped in the middleware stack.
    mock_middleware = MagicMock()
    del mock_middleware.__iter__

    @get("/", middleware=[mock_middleware])
    async def handler() -> None:
        pass

    route = HTTPRoute(path="/", route_handlers=[handler])
    build_route_middleware_stack(app=Litestar(), route=route, route_handler=handler)
    mock_middleware.assert_called_once()

    call_args = mock_middleware.call_args_list[0]
    assert len(call_args.args) == 1
    assert isinstance(call_args.args[0], ExceptionHandlerMiddleware)
    assert not call_args.kwargs


def test_conflicting_path_parameter_types_raise() -> None:
    # https://github.com/litestar-org/litestar/issues/3622

    @get("/{id:int}")
    async def int_handler(id: FromPath[int]) -> int:
        return id

    @get("/{id:str}")
    async def str_handler(id: FromPath[str]) -> str:
        return id

    with pytest.raises(ImproperlyConfiguredException, match="Path '/{id:str}' conflicts"):
        Litestar(route_handlers=[int_handler, str_handler])


def test_conflicting_path_parameter_names_raise() -> None:
    @get("/{first:int}/detail")
    async def first_handler(first: FromPath[int]) -> int:
        return first

    @get("/{second:int}/detail")
    async def second_handler(second: FromPath[int]) -> int:
        return second

    with pytest.raises(ImproperlyConfiguredException, match="Path '/{second:int}/detail' conflicts"):
        Litestar(route_handlers=[first_handler, second_handler])


def test_conflicting_websocket_path_parameter_types_raise() -> None:
    @websocket_listener("/{id:int}")
    async def int_handler(data: str, id: FromPath[int]) -> int:
        return id

    @websocket_listener("/{id:str}")
    async def str_handler(data: str, id: FromPath[str]) -> str:
        return id

    with pytest.raises(ImproperlyConfiguredException, match="Path '/{id:str}' conflicts"):
        Litestar(route_handlers=[int_handler, str_handler])


def test_differing_path_parameters_on_distinct_paths_do_not_conflict() -> None:
    # the path parameters share a trie node, but neither handler shadows the other

    @get("/{first:int}/first")
    async def first_handler(first: FromPath[int]) -> int:
        return first

    @get("/{second:str}/second")
    async def second_handler(second: FromPath[str]) -> str:
        return second

    @post("/{third:str}/first")
    async def third_handler(third: FromPath[str]) -> str:
        return third

    with create_test_client([first_handler, second_handler, third_handler]) as client:
        assert client.get("/1/first").json() == 1
        assert client.get("/1/second").text == "1"
        assert client.post("/1/first").text == "1"


def test_reconstructing_the_routing_trie_does_not_raise() -> None:
    # the trie is constructed anew for an already configured node when handlers are
    # registered on an app after its creation

    @get("/{id:int}")
    async def handler(id: FromPath[int]) -> int:
        return id

    app = Litestar(route_handlers=[handler])
    app.asgi_router.construct_routing_trie()
