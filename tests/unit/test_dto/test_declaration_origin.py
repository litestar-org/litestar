import inspect
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

import pytest

from litestar import Controller, Litestar, Router, get, post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.dto._plan import read_dto_declaration
from litestar.exceptions import LitestarException
from litestar.handlers import HTTPRouteHandler, WebsocketListener, asgi, websocket_stream
from litestar.params import JSONBody
from litestar.types import Empty, Receive, Scope, Send
from tests.unit.test_dto import registered

Option = Literal["dto", "return_dto"]


@dataclass
class User:
    id: int
    name: str


UserDTO = DataclassDTO[User]
UserReadDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"name"})]]


def declared(handler: Any, option: Option) -> tuple[Any, bool]:
    return read_dto_declaration(handler, is_data_field=option == "dto")


def _set(option: Option, value: Any) -> dict[str, Any]:
    return {option: value}


def _handler(**options: Any) -> HTTPRouteHandler:
    @get("/", **options)
    async def handler() -> User:
        return User(id=1, name="a")

    return handler


def _on_handler(option: Option) -> Any:
    return registered(Litestar([_handler(**_set(option, UserDTO))]), method="GET")


def _on_app(option: Option) -> Any:
    return registered(Litestar([_handler()], **_set(option, UserDTO)), method="GET")


def _on_router(option: Option) -> Any:
    return registered(Litestar([Router("/", route_handlers=[_handler()], **_set(option, UserDTO))]), method="GET")


def _controller(option: Option, value: Any, **method_options: Any) -> type[Controller]:
    class UserController(Controller):
        path = "/"

        @get(**method_options)
        async def handler(self) -> User:
            return User(id=1, name="a")

    setattr(UserController, option, value)
    return UserController


def _on_controller(option: Option) -> Any:
    return registered(Litestar([_controller(option, UserDTO)]), method="GET")


def _controller_and_method(option: Option) -> Any:
    return registered(Litestar([_controller(option, UserDTO, **_set(option, UserReadDTO))]), method="GET")


def _controller_and_method_none(option: Option) -> Any:
    return registered(Litestar([_controller(option, UserDTO, **_set(option, None))]), method="GET")


def _router_none_in_app(option: Option) -> Any:
    router = Router("/", route_handlers=[_handler()], **_set(option, None))
    return registered(Litestar([router], **_set(option, UserDTO)), method="GET")


def _nothing(option: Option) -> Any:
    return registered(Litestar([_handler()]), method="GET")


def _listener_class(option: Option) -> Any:
    class Listener(WebsocketListener):
        path = "/ws"

        async def on_receive(self, data: User) -> User:
            return data

    setattr(Listener, option, UserDTO)
    return registered(Litestar([Listener]), "/ws", "websocket")


def _websocket_stream(option: Option) -> Any:
    @websocket_stream("/ws", **_set(option, UserDTO))
    async def stream() -> AsyncGenerator[User, None]:
        yield User(id=1, name="a")

    return registered(Litestar([stream]), "/ws", "websocket")


def _asgi_under_router(option: Option) -> Any:
    @asgi("/asgi")
    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    app = Litestar([Router("/", route_handlers=[asgi_app], **_set(option, UserDTO))])
    return registered(app, "/asgi", "asgi")


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
    assert declared(build(option), option) == (value, source == "handler")


@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_handler_registered_on_two_routers_has_independent_inherited_values(option: Option) -> None:
    handler = _handler()
    first = Router("/first", route_handlers=[handler], **_set(option, UserDTO))
    second = Router("/second", route_handlers=[handler], **_set(option, UserReadDTO))

    app = Litestar([first, second])

    assert declared(registered(app, "/first", "GET"), option) == (UserDTO, False)
    assert declared(registered(app, "/second", "GET"), option) == (UserReadDTO, False)


def test_generated_options_handler_inherits_app_dtos_as_layer() -> None:
    app = Litestar([_handler()], dto=UserDTO, return_dto=UserReadDTO)
    options_handler = registered(app, "/", "OPTIONS")

    assert declared(options_handler, "dto") == (UserDTO, False)
    assert declared(options_handler, "return_dto") == (UserReadDTO, False)


@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_merge_twice_keeps_closest_layer(option: Option) -> None:
    closest = Router("/inner", route_handlers=[], **_set(option, UserDTO))
    outer = Router("/outer", route_handlers=[], **_set(option, UserReadDTO))

    merged = _handler().merge(closest).merge(outer)

    assert declared(merged, option) == (UserDTO, False)


@pytest.mark.parametrize("own", [Empty, UserReadDTO], ids=["inherited-only", "own-and-inherited"])
@pytest.mark.parametrize("option", ["dto", "return_dto"])
def test_with_changes_preserves_declarations(option: Option, own: Any) -> None:
    handler = _handler() if own is Empty else _handler(**_set(option, own))
    merged = handler.merge(Router("/", route_handlers=[], dto=UserDTO, return_dto=UserDTO))

    changed = merged._with_changes(path="/x")

    for name in ("dto", "return_dto"):
        assert declared(changed, name) == declared(merged, name)


def test_app_register_keeps_declarations_of_registered_handlers() -> None:
    app = Litestar([_handler()], dto=UserDTO)
    route_handler = registered(app, "/", "GET")

    @post("/other", dto=UserReadDTO)
    async def other(data: JSONBody[User]) -> User:
        return data

    app.register(other)

    assert declared(route_handler, "dto") == (UserDTO, False)
    assert declared(registered(app, "/other", "POST"), "dto") == (UserReadDTO, True)


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
    handler = registered(app, "/", "GET")

    assert "inherited_dto" not in handler.opt
    assert "inherited_return_dto" not in handler.opt


def test_unregistered_merged_handler_reports_inherited_dto() -> None:
    merged = _handler().merge(Router("/", route_handlers=[], dto=UserDTO))

    assert merged.data_dto is UserDTO
    with pytest.raises(LitestarException):
        merged.return_dto


_BASE_PARAMETERS = set(inspect.signature(HTTPRouteHandler.__init__).parameters)


class StrictHandler(HTTPRouteHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **{key: value for key, value in kwargs.items() if key in _BASE_PARAMETERS})


def test_handler_subclass_with_strict_signature_keeps_layer_dto() -> None:
    async def handler() -> User:
        return User(id=1, name="a")

    route_handler = StrictHandler("/", fn=handler, http_method="GET")

    app = Litestar([Router("/", route_handlers=[route_handler], dto=UserDTO)])

    assert declared(registered(app, "/", "GET"), "dto") == (UserDTO, False)
