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
    assert app._route_name_to_path_map["handler-name"]["path"] == "/router-path/path-one/{param:str}"
    assert app._route_name_to_path_map["handler-name"]["handler"] == handler
    assert app._route_name_to_path_map["asgi-name"]["path"] == "/asgi-path"
    assert app._route_name_to_path_map["asgi-name"]["handler"] == asgi_handler
    assert app._route_name_to_path_map["websocket-name"]["path"] == "/websocket-path"
    assert app._route_name_to_path_map["websocket-name"]["handler"] == websocket_handler
