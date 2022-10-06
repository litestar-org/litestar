from typing import Any, Type

import pytest

from starlite import (
    Controller,
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
def test_default_indexes_handlers(decorator: Type[HTTPRouteHandler]) -> None:
    @decorator("/handler")  # type: ignore
    def handler() -> None:
        pass

    @decorator("/named_handler", name="named_handler")  # type: ignore
    def named_handler() -> None:
        pass

    class MyController(Controller):
        path = "/test"

        @decorator()  # type: ignore
        def handler(self) -> None:
            pass

    router = Router("router/", route_handlers=[handler, named_handler, MyController])
    app = Starlite(route_handlers=[router])

    handler_index = app.get_handler_index_by_name(handler.fn.__qualname__)  # type: ignore
    assert handler_index
    assert handler_index["paths"] == ["/router/handler"]
    assert handler_index["handler"] == handler
    assert handler_index["qualname"] == handler.fn.__qualname__  # type: ignore

    handler_index = app.get_handler_index_by_name(MyController.handler.fn.__qualname__)  # type: ignore
    assert handler_index
    assert handler_index["paths"] == ["/router/test"]
    # we can not do an assertion on handlers in Controller subclasses
    assert handler_index["qualname"] == MyController.handler.fn.__qualname__  # type: ignore

    # test that passing route name overrides default name completely
    handler_index = app.get_handler_index_by_name(named_handler.fn.__qualname__)  # type: ignore
    assert handler_index is None


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
