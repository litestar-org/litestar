from typing import Any, Type

import pytest

from starlite import (
    HTTPRouteHandler,
    Router,
    Starlite,
    asgi,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)


@pytest.mark.parametrize("decorator", [get, post, patch, put, delete])
def test_indexes_handlers(decorator: Type[HTTPRouteHandler]) -> None:
    @decorator("/path-one/{param:str}", name="handler-name")  # type: ignore
    def handler() -> None:
        return None

    @asgi("/asgi-path", name="asgi-name")
    async def asgi_handler(scope: Any, receive: Any, send: Any) -> None:
        pass

    @websocket("/websocket-path", name="websocket-name")
    async def websocket_handler(socket: Any) -> None:
        pass

    router = Router("router-path/", route_handlers=[handler])
    app = Starlite(route_handlers=[router, websocket_handler, asgi_handler])

    handler_index = app.get_handler_index_by_name("handler-name")
    assert handler_index
    assert handler_index["path"] == "/router-path/path-one/{param:str}"
    assert handler_index["handler"] == handler

    handler_index = app.get_handler_index_by_name("asgi-name")
    assert handler_index
    assert handler_index["path"] == "/asgi-path"
    assert handler_index["handler"] == asgi_handler

    handler_index = app.get_handler_index_by_name("websocket-name")
    assert handler_index
    assert handler_index["path"] == "/websocket-path"
    assert handler_index["handler"] == websocket_handler

    assert app.get_handler_index_by_name("nope") is None
