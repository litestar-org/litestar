from typing import Any, Type

import pytest

from starlite import (
    HTTPRouteHandler,
    ImproperlyConfiguredException,
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
    assert handler_index["paths"] == ["/router-path/path-one/{param:str}"]
    assert handler_index["handler"] == handler

    handler_index = app.get_handler_index_by_name("asgi-name")
    assert handler_index
    assert handler_index["paths"] == ["/asgi-path"]
    assert handler_index["handler"] == asgi_handler

    handler_index = app.get_handler_index_by_name("websocket-name")
    assert handler_index
    assert handler_index["paths"] == ["/websocket-path"]
    assert handler_index["handler"] == websocket_handler

    assert app.get_handler_index_by_name("nope") is None


@pytest.mark.parametrize("decorator", [get, post, patch, put, delete])
def test_indexes_handlers_with_multiple_paths(decorator: Type[HTTPRouteHandler]) -> None:
    @decorator(["/path-one", "/path-one/{param:str}"], name="handler")  # type: ignore
    def handler() -> None:
        return None

    @decorator(["/path-two"], name="handler-two")  # type: ignore
    def handler_two() -> None:
        return None

    router = Router("router-one/", route_handlers=[handler_two])
    router_two = Router("router-two/", route_handlers=[handler_two])

    app = Starlite(route_handlers=[router, router_two, handler])

    handler_index = app.get_handler_index_by_name("handler")
    assert handler_index
    assert handler_index["paths"] == ["/path-one", "/path-one/{param:str}"]
    assert handler_index["handler"] == handler

    handler_index = app.get_handler_index_by_name("handler-two")
    assert handler_index
    assert handler_index["paths"] == ["/router-one/path-two", "/router-two/path-two"]
    assert handler_index["handler"] == handler_two


def test_indexing_validation() -> None:
    @get("/abc", name="same-name")
    def handler_one() -> None:
        pass

    @get("/xyz", name="same-name")
    def handler_two() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_one, handler_two])
