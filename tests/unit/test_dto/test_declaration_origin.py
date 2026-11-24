from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

import pytest

from litestar import Controller, Litestar, Router, get, post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.dto._plan import DTODeclaration, read_dto_declaration
from litestar.exceptions import LitestarException
from litestar.handlers import HTTPRouteHandler, WebsocketListener, asgi, websocket_stream
from litestar.params import JSONBody
from litestar.types import Empty, Receive, Scope, Send

Option = Literal["dto", "return_dto"]


@dataclass
class User:
    id: int
    name: str


UserDTO = DataclassDTO[User]
UserReadDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"name"})]]


def _set(option: Option, value: Any) -> dict[str, Any]:
    return {option: value}


def _handler(**options: Any) -> HTTPRouteHandler:
    @get("/", **options)
    async def handler() -> User:
        return User(id=1, name="a")

    return handler


def _http(app: Litestar, path: str = "/", method: Any = "GET") -> Any:
    return app.route_handler_method_map[path][method]


def _on_handler(option: Option) -> Any:
    return _http(Litestar([_handler(**_set(option, UserDTO))]))


def _on_app(option: Option) -> Any:
    return _http(Litestar([_handler()], **_set(option, UserDTO)))


def _on_router(option: Option) -> Any:
    return _http(Litestar([Router("/", route_handlers=[_handler()], **_set(option, UserDTO))]))


def _controller(option: Option, value: Any, **method_options: Any) -> type[Controller]:
    class UserController(Controller):
        path = "/"

        @get(**method_options)
        async def handler(self) -> User:
            return User(id=1, name="a")

    setattr(UserController, option, value)
    return UserController


def _on_controller(option: Option) -> Any:
    return _http(Litestar([_controller(option, UserDTO)]))


def _controller_and_method(option: Option) -> Any:
    return _http(Litestar([_controller(option, UserDTO, **_set(option, UserReadDTO))]))


def _controller_and_method_none(option: Option) -> Any:
    return _http(Litestar([_controller(option, UserDTO, **_set(option, None))]))


def _router_none_in_app(option: Option) -> Any:
    router = Router("/", route_handlers=[_handler()], **_set(option, None))
    return _http(Litestar([router], **_set(option, UserDTO)))


def _nothing(option: Option) -> Any:
    return _http(Litestar([_handler()]))


def _listener_class(option: Option) -> Any:
    class Listener(WebsocketListener):
        path = "/ws"

        async def on_receive(self, data: User) -> User:
            return data

    setattr(Listener, option, UserDTO)
    return Litestar([Listener]).route_handler_method_map["/ws"]["websocket"]


def _websocket_stream(option: Option) -> Any:
    @websocket_stream("/ws", **_set(option, UserDTO))
    async def stream() -> AsyncGenerator[User, None]:
        yield User(id=1, name="a")

    return Litestar([stream]).route_handler_method_map["/ws"]["websocket"]


def _asgi_under_router(option: Option) -> Any:
    @asgi("/asgi")
    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    app = Litestar([Router("/", route_handlers=[asgi_app], **_set(option, UserDTO))])
    return app.route_handler_method_map["/asgi"]["asgi"]


@pytest.mark.parametrize("option", ["dto", "return_dto"])
@pytest.mark.parametrize(
    ("build", "value", "source"),
    [
        pytest.param(_on_handler, UserDTO, "handler", id="handler"),
        pytest.param(_on_app, UserDTO, "layer", id="app"),
        pytest.param(_on_router, UserDTO, "layer", id="router"),
        pytest.param(_on_controller, UserDTO, "layer", id="controller"),
        pytest.param(_controller_and_method, UserReadDTO, "handler", id="controller-and-method"),
        pytest.param(_controller_and_method_none, None, "handler", id="controller-and-method-none"),
        pytest.param(_router_none_in_app, None, "layer", id="router-none-in-app"),
        pytest.param(_nothing, Empty, None, id="nothing"),
        pytest.param(_listener_class, UserDTO, "handler", id="listener-class"),
        pytest.param(_websocket_stream, UserDTO, "handler", id="websocket-stream"),
        pytest.param(_asgi_under_router, UserDTO, "layer", id="asgi-under-router"),
    ],
)
def test_declaration_source(build: Callable[[Option], Any], value: Any, source: Any, option: Option) -> None:
    assert read_dto_declaration(build(option), option) == DTODeclaration(option=option, value=value, source=source)


@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_handler_registered_on_two_routers_has_independent_inherited_values(option: Option) -> None:
    handler = _handler()
    first = Router("/first", route_handlers=[handler], **_set(option, UserDTO))
    second = Router("/second", route_handlers=[handler], **_set(option, UserReadDTO))

    app = Litestar([first, second])

    assert read_dto_declaration(_http(app, "/first"), option) == DTODeclaration(option, UserDTO, "layer")
    assert read_dto_declaration(_http(app, "/second"), option) == DTODeclaration(option, UserReadDTO, "layer")


def test_generated_options_handler_inherits_app_dtos_as_layer() -> None:
    app = Litestar([_handler()], dto=UserDTO, return_dto=UserReadDTO)
    options_handler = _http(app, method="OPTIONS")

    assert read_dto_declaration(options_handler, "dto") == DTODeclaration("dto", UserDTO, "layer")
    assert read_dto_declaration(options_handler, "return_dto") == DTODeclaration("return_dto", UserReadDTO, "layer")


@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_merge_twice_keeps_closest_layer(option: Option) -> None:
    closest = Router("/inner", route_handlers=[], **_set(option, UserDTO))
    outer = Router("/outer", route_handlers=[], **_set(option, UserReadDTO))

    merged = _handler().merge(closest).merge(outer)

    assert read_dto_declaration(merged, option) == DTODeclaration(option, UserDTO, "layer")


@pytest.mark.parametrize("own", [Empty, UserReadDTO])
@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_with_changes_preserves_declarations(option: Option, own: Any) -> None:
    handler = _handler() if own is Empty else _handler(**_set(option, own))
    merged = handler.merge(Router("/", route_handlers=[], dto=UserDTO, return_dto=UserDTO))

    changed = merged._with_changes(path="/x")

    for name in ("dto", "return_dto"):
        assert read_dto_declaration(changed, name) == read_dto_declaration(merged, name)


def test_app_register_keeps_declarations_of_registered_handlers() -> None:
    app = Litestar([_handler()], dto=UserDTO)
    registered = _http(app)

    @post("/other", dto=UserReadDTO)
    async def other(data: JSONBody[User]) -> User:
        return data

    app.register(other)

    assert read_dto_declaration(registered, "dto") == DTODeclaration("dto", UserDTO, "layer")
    assert read_dto_declaration(_http(app, "/other", "POST"), "dto") == DTODeclaration("dto", UserReadDTO, "handler")


def test_user_held_handler_is_not_mutated() -> None:
    handler = _handler(dto=UserDTO)

    Litestar([Router("/", route_handlers=[handler], return_dto=UserReadDTO)], dto=UserReadDTO)

    assert handler._dto is UserDTO
    assert handler._return_dto is Empty
    assert handler._inherited_dto is Empty
    assert handler._inherited_return_dto is Empty
    assert handler._dto_plan is None


def test_inherited_keywords_do_not_leak_into_opt() -> None:
    app = Litestar([Router("/", route_handlers=[_handler()], dto=UserDTO, return_dto=UserReadDTO)])
    handler = _http(app)

    assert "inherited_dto" not in handler.opt
    assert "inherited_return_dto" not in handler.opt


def test_unregistered_merged_handler_reports_inherited_dto() -> None:
    merged = _handler().merge(Router("/", route_handlers=[], dto=UserDTO))

    assert merged.data_dto is UserDTO
    with pytest.raises(LitestarException):
        merged.return_dto


class ForwardingHandler(HTTPRouteHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class SwallowingHandler(HTTPRouteHandler):
    def __init__(self, *args: Any, inherited_dto: Any = Empty, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


@pytest.mark.parametrize(
    ("handler_cls", "expected"),
    [
        pytest.param(ForwardingHandler, DTODeclaration("dto", UserDTO, "layer"), id="forwarding"),
        pytest.param(SwallowingHandler, DTODeclaration("dto", Empty, None), id="swallowing"),
    ],
)
def test_handler_subclass_forwarding_kwargs_keeps_layer_dto(
    handler_cls: type[HTTPRouteHandler], expected: DTODeclaration
) -> None:
    async def handler() -> User:
        return User(id=1, name="a")

    route_handler = handler_cls("/", fn=handler, http_method="GET")

    app = Litestar([Router("/", route_handlers=[route_handler], dto=UserDTO)])

    assert read_dto_declaration(_http(app), "dto") == expected
