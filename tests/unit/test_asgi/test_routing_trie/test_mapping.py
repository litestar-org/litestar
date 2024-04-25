from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from litestar import Litestar, get
from litestar._asgi.routing_trie.mapping import build_route_middleware_stack
from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware
from litestar.routes import HTTPRoute


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
    mock_middleware = AsyncMock()
    del mock_middleware.__iter__

    @get("/", middleware=[mock_middleware])
    async def handler() -> None:
        pass

    route = HTTPRoute(path="/", route_handlers=[handler])
    build_route_middleware_stack(app=Litestar(), route=route, route_handler=handler)
    mock_middleware.assert_called_once()
    ((_, kw_args),) = mock_middleware.call_args_list
    assert isinstance(kw_args["app"], ExceptionHandlerMiddleware)
