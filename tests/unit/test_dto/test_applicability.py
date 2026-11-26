import copy
import pickle
from collections.abc import AsyncGenerator, Callable, Iterable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, NewType, Optional, TypeVar, Union

import pytest

from litestar import Controller, Litestar, Response, Router, get, post, websocket_listener, websocket_stream
from litestar.di._route_handler import HandlerErrorPrefix
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData
from litestar.dto._applicability import resolve_dto_target
from litestar.enums import RequestEncodingType
from litestar.exceptions import (
    DTOFactoryException,
    DTONotApplicableError,
    DTOTransferTypeError,
    ImproperlyConfiguredException,
    InvalidAnnotationException,
    MissingDTOError,
)
from litestar.handlers import WebsocketListener
from litestar.params import BodyKwarg, JSONBody, MultipartBody, URLEncodedBody
from litestar.plugins import SerializationPlugin
from litestar.response import ServerSentEvent, Stream
from litestar.testing import TestClient, create_test_client
from litestar.types import Empty
from litestar.typing import FieldDefinition

T = TypeVar("T")

Placement = Literal["handler", "controller", "router", "app"]
NO_BODY: Any = object()
JSON_BODY: Any = JSONBody


@dataclass
class User:
    id: int
    name: str
    secret: str = "s"


@dataclass
class Other:
    a: int
    hidden: str = "h"


@dataclass
class Wrapper(Generic[T]):
    data: T


@dataclass
class Page(Generic[T]):
    data: T
    cursor: str = "c"


@dataclass
class Items(Generic[T]):
    items: T


@dataclass
class U1:
    a: int


@dataclass
class U2:
    b: int


@dataclass
class UnionHolder:
    f: Union[U1, U2]


@dataclass
class Two(Generic[T]):
    first: T
    rest: list[T]


@dataclass
class Owned(Generic[T]):
    data: T
    owner: User


@dataclass
class Outer(Generic[T]):
    inner: Wrapper[T]


UserId = NewType("UserId", int)


UserDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"secret"})]]
OtherDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"hidden"})]]
OtherPluginDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"a"})]]

USER = User(id=1, name="a", secret="x")
USER_IN = {"id": 1, "name": "a", "secret": "x"}
USER_ENCODED = {"id": 1, "name": "a"}
USER_DECODED = {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}}
OTHER = Other(a=1, hidden="x")
OTHER_FULL = {"a": 1, "hidden": "x"}


class ModelPlugin(SerializationPlugin):
    def __init__(self, model: type[Any], dto: type[AbstractDTO[Any]]) -> None:
        self.model = model
        self.dto = dto

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(self.model)

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO[Any]]:
        return self.dto


class VetoDTO(DataclassDTO[User]):
    @classmethod
    def is_supported_model_type_field(cls, field_definition: FieldDefinition) -> bool:
        return False


def _fn(body: Any, returns: Any, respond: Callable[[Any], Any], with_self: bool) -> Any:
    fn: Any
    if body is NO_BODY and with_self:

        async def method(self: Any) -> Any:
            return respond(None)

        fn = method
    elif body is NO_BODY:

        async def handler() -> Any:
            return respond(None)

        fn = handler
    elif with_self:

        async def method_with_data(self: Any, data: Any) -> Any:
            return respond(data)

        fn = method_with_data
    else:

        async def handler_with_data(data: Any) -> Any:
            return respond(data)

        fn = handler_with_data
    fn.__annotations__ = {"return": returns} if body is NO_BODY else {"data": body, "return": returns}
    return fn


def build_app(
    placement: Placement,
    *,
    method: Literal["GET", "POST"] = "POST",
    body: Any = NO_BODY,
    returns: Any = None,
    respond: Callable[[Any], Any] = lambda data: None,
    plugins: tuple[SerializationPlugin, ...] = (),
    handler_options: dict[str, Any] | None = None,
    **options: Any,
) -> Litestar:
    decorator: Any = post if method == "POST" else get
    handler_options = dict(handler_options or {})
    if placement == "handler":
        handler_options.update(options)
        options = {}
    route_handlers: list[Any]
    if placement == "controller":
        route_handler = decorator(**handler_options)(_fn(body, returns, respond, with_self=True))
        route_handlers = [type("LayerController", (Controller,), {"path": "/", "handler": route_handler, **options})]
        options = {}
    else:
        route_handlers = [decorator("/", **handler_options)(_fn(body, returns, respond, with_self=False))]
        if placement == "router":
            route_handlers = [Router("/", route_handlers=route_handlers, **options)]
            options = {}
    return Litestar(route_handlers, plugins=list(plugins), openapi_config=None, **options)


def registered(app: Litestar, method: Any = "POST") -> Any:
    return app.route_handler_method_map["/"][method]


def _target(annotation: Any, is_data_field: bool) -> Any:
    target = resolve_dto_target(UserDTO, FieldDefinition.from_annotation(annotation), is_data_field=is_data_field)
    if target is None:
        return None
    wrapped_passes_none = target.wrapper_attribute_name is not None and target.transfer_field.is_optional
    return target.wrapper_attribute_name, target.passes_none, wrapped_passes_none


PLAIN = (None, False, False)
OPTIONAL = (None, True, False)
DATA_ONLY: Any = object()


@pytest.mark.parametrize(
    ("annotation", "data", "return_"),
    [
        pytest.param(User, PLAIN, PLAIN, id="model"),
        pytest.param(list[User], PLAIN, PLAIN, id="list"),
        pytest.param(dict[str, User], PLAIN, PLAIN, id="mapping"),
        pytest.param(tuple[User, ...], PLAIN, PLAIN, id="variadic-tuple"),
        pytest.param(Optional[User], OPTIONAL, OPTIONAL, id="optional"),
        pytest.param(Optional[list[User]], OPTIONAL, OPTIONAL, id="optional-list"),
        pytest.param(User | Other | None, None, None, id="optional-union-model-first"),
        pytest.param(Other | User | None, None, None, id="optional-union-other-first"),
        pytest.param(list[User | int | None], None, None, id="list-of-optional-union"),
        pytest.param(DTOData[User], PLAIN, PLAIN, id="dto-data"),
        pytest.param(Optional[DTOData[User]], OPTIONAL, OPTIONAL, id="optional-dto-data"),
        pytest.param(Wrapper[User], None, ("data", False, False), id="wrapper"),
        pytest.param(Wrapper[list[User]], None, ("data", False, False), id="wrapper-list"),
        pytest.param(Response[User], None, ("content", False, False), id="response"),
        pytest.param(Response[Optional[User]], None, ("content", False, True), id="response-optional"),
        pytest.param(Optional[Wrapper[User]], None, ("data", True, False), id="optional-wrapper"),
        pytest.param(Optional[Response[Optional[User]]], None, ("content", True, True), id="optional-response"),
        pytest.param(list[Wrapper[User]], None, None, id="list-of-wrappers"),
        pytest.param(Wrapper[User] | Page[User] | None, None, ("data", True, False), id="union-of-wrappers"),
        pytest.param(Wrapper[User] | Items[User], None, None, id="union-of-wrappers-with-other-attributes"),
        pytest.param(Wrapper[User] | int, None, None, id="union-of-wrapper-and-int"),
        pytest.param(AsyncGenerator[User, None], None, None, id="async-generator"),
        pytest.param(dict[User, int], None, None, id="model-as-key"),
        pytest.param(tuple[User, int], None, None, id="tuple"),
        pytest.param(Union[User, Other], None, None, id="union"),
        pytest.param(ServerSentEvent, None, None, id="sse"),
        pytest.param(Stream, None, None, id="stream"),
        pytest.param(Any, None, None, id="any"),
        pytest.param(Other, None, None, id="other"),
        pytest.param(None, None, None, id="none"),
        pytest.param(Empty, None, None, id="missing"),
        pytest.param(list, None, None, id="bare-list"),
        pytest.param(list[DTOData], None, None, id="list-of-bare-dto-data"),
        pytest.param(URLEncodedBody[User], PLAIN, DATA_ONLY, id="form-model"),
        pytest.param(
            Annotated[Optional[User], BodyKwarg(media_type=RequestEncodingType.MULTI_PART)],
            OPTIONAL,
            DATA_ONLY,
            id="form-optional",
        ),
        pytest.param(MultipartBody[DTOData[User]], PLAIN, DATA_ONLY, id="form-dto-data"),
        pytest.param(MultipartBody[list[User]], None, DATA_ONLY, id="form-list"),
        pytest.param(URLEncodedBody[dict[str, User]], None, DATA_ONLY, id="form-mapping"),
    ],
)
def test_resolve_dto_target(annotation: Any, data: Any, return_: Any) -> None:
    assert _target(annotation, True) == data
    if return_ is not DATA_ONLY:
        assert _target(annotation, False) == return_


def describe(data: Any) -> dict[str, Any]:
    return {"type": type(data).__name__, "data": data}


PLUGIN = (ModelPlugin(User, UserDTO),)
PLUGIN_OPTIONS = {"plugins": PLUGIN}
OTHER_PLUGIN = (ModelPlugin(Other, OtherPluginDTO),)
SKIPPED = {"type": "Other", "data": OTHER_FULL}
DTO = {"dto": UserDTO}
RETURN_DTO = {"return_dto": UserDTO}
NA = DTONotApplicableError
MISSING = MissingDTOError
NOT_APPLIED: Any = object()
TUPLE = tuple[User, int]
STREAM = AsyncGenerator[User, None]
OPTIONAL_UNION = User | int | None
JSON_TUPLE = Annotated[tuple[User, int], BodyKwarg(media_type=RequestEncodingType.JSON)]


@pytest.mark.parametrize(
    ("placement", "options", "body", "plugins", "payload", "expected"),
    [
        pytest.param("handler", DTO, JSONBody[User], (), USER_IN, USER_DECODED, id="handler"),
        pytest.param("app", DTO, JSONBody[User], (), USER_IN, USER_DECODED, id="layer"),
        pytest.param("handler", DTO, JSONBody[Other], (), None, NA, id="handler-other-model"),
        pytest.param("app", DTO, JSONBody[Other], (), OTHER_FULL, SKIPPED, id="app-other-model"),
        pytest.param("router", DTO, JSONBody[Other], (), OTHER_FULL, SKIPPED, id="router-other-model"),
        pytest.param("controller", DTO, JSONBody[Other], (), OTHER_FULL, SKIPPED, id="controller-other-model"),
        pytest.param("app", DTO, JSONBody[str], (), "x", {"type": "str", "data": "x"}, id="layer-str"),
        pytest.param("app", DTO, JSON_BODY[tuple[User, int]], (), None, NA, id="layer-tuple"),
        pytest.param("controller", DTO, JSON_BODY[Union[User, Other]], (), None, NA, id="layer-union"),
        pytest.param("app", DTO, JSON_BODY[dict[str, tuple[User, int]]], (), None, NA, id="layer-mapping-of-tuple"),
        pytest.param("app", DTO, JSON_BODY[User | int | None], (), None, NA, id="layer-optional-union"),
        pytest.param("handler", DTO, JSONBody[Wrapper[User]], (), None, NA, id="handler-wrapper"),
        pytest.param("handler", DTO, JSONBody[dict], (), None, NA, id="handler-bare-dict"),
        pytest.param("app", DTO, JSONBody[dict], (), {}, {"type": "dict", "data": {}}, id="layer-bare-dict"),
        pytest.param("handler", DTO, MultipartBody[list[User]], (), None, NA, id="handler-form-list"),
        pytest.param("app", DTO, MultipartBody[list[User]], (), None, NA, id="layer-form-list"),
        pytest.param("app", {}, JSONBody[User], PLUGIN, USER_IN, USER_DECODED, id="plugin"),
        pytest.param("router", {"dto": None}, JSONBody[User], PLUGIN, USER_IN, describe(USER_IN) | {"type": "User"}),
        pytest.param("app", {}, JSON_TUPLE, PLUGIN, None, NA, id="plugin-tuple"),
        pytest.param("app", {}, JSON_BODY[User | int | None], PLUGIN, None, NA, id="plugin-optional-union"),
        pytest.param("app", {}, JSON_BODY[list[User] | int | None], PLUGIN, None, NA, id="plugin-list-member"),
        pytest.param("app", {}, JSON_BODY[list[User | Other | None]], PLUGIN, None, NA, id="plugin-nested-union"),
        pytest.param("app", {}, JSONBody[DTOData[User]], (), None, MISSING, id="dto-data"),
        pytest.param("app", {}, JSON_BODY[Optional[DTOData[User]]], (), None, MISSING, id="optional-dto-data"),
        pytest.param("controller", DTO, JSONBody[DTOData[Other]], (), None, MISSING, id="dto-data-skipped-dto"),
    ],
)
def test_data_dto_declaration_origin(
    placement: Placement, options: dict[str, Any], body: Any, plugins: Any, payload: Any, expected: Any
) -> None:
    def build() -> Litestar:
        return build_app(
            placement,
            body=body,
            returns=dict[str, Any],
            respond=describe,
            plugins=plugins,
            handler_options={"return_dto": None},
            **options,
        )

    if isinstance(expected, type):
        with pytest.raises(expected):
            build()
        return

    with TestClient(build()) as client:
        response = client.post("/", json=payload)
    assert response.status_code == 201
    assert response.json() == expected


@pytest.mark.parametrize(
    ("placement", "options", "handler_options", "returns", "value", "plugins", "expected"),
    [
        pytest.param("handler", RETURN_DTO, {}, User, USER, (), USER_ENCODED, id="handler"),
        pytest.param("app", RETURN_DTO, {}, User, USER, (), USER_ENCODED, id="layer"),
        pytest.param("handler", DTO, {}, User, USER, (), USER_ENCODED, id="data-dto-reused"),
        pytest.param("handler", RETURN_DTO, {}, Other, OTHER, (), NA, id="handler-other-model"),
        pytest.param("handler", RETURN_DTO, {}, None, None, (), NA, id="handler-none"),
        pytest.param("handler", RETURN_DTO, {}, Any, USER, (), NA, id="handler-any"),
        pytest.param("handler", RETURN_DTO, {}, ServerSentEvent, None, (), NA, id="handler-sse"),
        pytest.param("handler", RETURN_DTO, {}, list, [], (), NA, id="handler-bare-list"),
        pytest.param("app", RETURN_DTO, {}, list, [], (), NOT_APPLIED, id="layer-bare-list"),
        pytest.param("app", RETURN_DTO, {}, Stream, None, (), NOT_APPLIED, id="layer-stream"),
        pytest.param("app", RETURN_DTO, {}, Other, OTHER, (), OTHER_FULL, id="layer-other-model"),
        pytest.param("app", RETURN_DTO, {}, str, "text", (), "text", id="layer-str"),
        pytest.param("app", RETURN_DTO, {}, tuple[User, int], None, (), NA, id="layer-tuple"),
        pytest.param("app", RETURN_DTO, {"return_dto": None}, tuple[User, int], (USER, 2), (), [USER_IN, 2]),
        pytest.param("handler", DTO, {}, Union[int, User], USER, (), NA, id="handler-dto-reused-union"),
        pytest.param("app", DTO, {}, Union[int, User], USER, (), NA, id="layer-dto-reused-union"),
        pytest.param("router", {"return_dto": None}, DTO, User, USER, (), USER_IN, id="layer-none-disables-reuse"),
        pytest.param("app", RETURN_DTO, {"dto": OtherDTO}, Other, OTHER, OTHER_PLUGIN, OTHER_FULL, id="skip-is-final"),
        pytest.param("handler", {"dto": OtherDTO}, {}, Other, OTHER, OTHER_PLUGIN, {"a": 1}, id="dto-beats-plugin"),
        pytest.param("app", {}, {}, Other, OTHER, (ModelPlugin(Other, OtherDTO),), {"a": 1}, id="plugin"),
        pytest.param("app", {}, {}, tuple[User, int], (USER, 2), PLUGIN, NA, id="plugin-tuple"),
        pytest.param("app", {}, {}, Union[User, Other], USER, PLUGIN, NA, id="plugin-union-without-none"),
        pytest.param("app", {}, {}, Wrapper[User] | int | None, None, PLUGIN, NA, id="plugin-wrapper-union"),
        pytest.param("app", {}, {}, list[User | Other | None], None, PLUGIN, NA, id="plugin-nested-union"),
        pytest.param("handler", {"return_dto": VetoDTO}, {}, User, USER, (), NA, id="handler-veto"),
        pytest.param("app", {"return_dto": VetoDTO}, {}, User, USER, (), USER_IN, id="layer-veto"),
    ],
)
def test_return_dto_declaration_origin(
    placement: Placement,
    options: dict[str, Any],
    handler_options: dict[str, Any],
    returns: Any,
    value: Any,
    plugins: Any,
    expected: Any,
) -> None:
    def build() -> Litestar:
        return build_app(
            placement,
            method="GET",
            returns=returns,
            respond=lambda _: value,
            plugins=plugins,
            handler_options=handler_options,
            **options,
        )

    if isinstance(expected, type):
        with pytest.raises(expected):
            build()
        return

    app = build()
    if expected is NOT_APPLIED:
        assert registered(app, "GET").return_backend is None
        return
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert (response.text if isinstance(expected, str) else response.json()) == expected


def test_skipped_layer_data_dto_validates_body_and_is_reused_for_return() -> None:
    app = build_app("controller", body=JSONBody[Other], returns=list[User], respond=lambda _: [USER], dto=UserDTO)
    without_dto = build_app("controller", body=JSONBody[Other], returns=list[User], respond=lambda _: [USER])

    with TestClient(app) as client, TestClient(without_dto) as plain:
        assert client.post("/", json=OTHER_FULL).json() == [USER_ENCODED]
        assert client.post("/", json={"a": "x"}).json() == plain.post("/", json={"a": "x"}).json()
    assert registered(app).data_dto is UserDTO
    assert registered(app).data_backend is None


class BaseUserListener(WebsocketListener):
    return_dto = UserDTO

    async def on_receive(self, data: str) -> Any:
        return None


class InheritingTextListener(BaseUserListener):
    path = "/ws"

    async def on_receive(self, data: str) -> str:
        return data


class InheritingUserListener(BaseUserListener):
    path = "/ws"

    async def on_receive(self, data: str) -> User:
        return USER


class OwnTextListener(BaseUserListener):
    path = "/ws"
    return_dto = UserDTO

    async def on_receive(self, data: str) -> str:
        return data


class DTODataListener(WebsocketListener):
    path = "/ws"

    async def on_receive(self, data: DTOData[User]) -> None: ...


def _listener(data: Any, returns: Any = str, **options: Any) -> Any:
    async def listener(data: Any) -> Any:
        return data if isinstance(data, str) else f"{type(data).__name__}:{data.secret}"

    listener.__annotations__ = {"data": data, "return": returns}
    return websocket_listener("/ws", **options)(listener)


@pytest.mark.parametrize(
    ("handler", "app_options", "sent", "expected"),
    [
        pytest.param(_listener(str, dto=UserDTO), {}, None, DTONotApplicableError, id="handler-str"),
        pytest.param(_listener(str), {"dto": UserDTO}, "text", "text", id="layer-str"),
        pytest.param(_listener(User, dto=UserDTO), {}, USER_IN, "User:s", id="handler-model"),
        pytest.param(_listener(DTOData[User]), {}, None, MissingDTOError, id="dto-data"),
        pytest.param(_listener(Optional[DTOData[User]]), {}, None, MissingDTOError, id="optional-dto-data"),
        pytest.param(DTODataListener, {}, None, MissingDTOError, id="dto-data-class"),
        pytest.param(InheritingTextListener, {}, "text", "text", id="inherited-return-dto-skipped"),
        pytest.param(InheritingUserListener, {}, "text", '{"id":1,"name":"a"}', id="inherited-return-dto"),
        pytest.param(OwnTextListener, {}, None, DTONotApplicableError, id="class-body-return-dto"),
    ],
)
def test_listener_declaration_origin(handler: Any, app_options: dict[str, Any], sent: Any, expected: Any) -> None:
    if isinstance(expected, type):
        with pytest.raises(expected):
            Litestar([handler], openapi_config=None, **app_options)
        return

    app = Litestar([handler], openapi_config=None, **app_options)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        if isinstance(sent, str):
            ws.send_text(sent)
        else:
            ws.send_json(sent)
        assert ws.receive_text() == expected


LAYER, HANDLER = "is declared on a layer", "is declared on the handler"
PLUGIN_NAME = "DataclassDTO[User] is created by a serialization plugin"
OPT_OUT_DTO = " Declare 'dto=None' on the handler to opt out."
OPT_OUT_RETURN = " Declare 'return_dto=None' on the handler to opt out."
STREAMED = " Streamed items are not transferred by a DTO."
FORM_ONE = " A form body is decoded into one model, not a collection."
RETURN_ONLY = " A generic wrapper is supported for return values only."
MANY = " More than one attribute of the generic wrapper holds the model: {}."
VETO = (
    "'return_dto=VetoDTO' is declared on the handler, but VetoDTO.is_supported_model_type_field() declines its return "
    "value annotated 'User'."
)


def _cannot(option: str | None, declared: str, data: bool, annotation: Any, tail: str = "") -> str:
    name = f"'{option}=DataclassDTO[User]' {declared}" if option else PLUGIN_NAME
    action = "decode its request body" if data else "encode its return value"
    text = annotation if isinstance(annotation, str) else repr(annotation)
    return f"{name}, but cannot {action} annotated '{text}': the DTO handles 'User'.{tail}"


@pytest.mark.parametrize(
    ("placement", "options", "marker", "annotation", "message"),
    [
        ("handler", DTO, JSON_BODY, dict[str, Any], _cannot("dto", HANDLER, True, "dict[str, typing.Any]")),
        ("app", RETURN_DTO, None, TUPLE, _cannot("return_dto", LAYER, False, TUPLE, OPT_OUT_RETURN)),
        ("app", DTO, None, Union[int, User], _cannot("dto", LAYER, False, Union[int, User], OPT_OUT_RETURN)),
        (
            "app",
            {"plugins": PLUGIN},
            JSON_BODY,
            OPTIONAL_UNION,
            _cannot(None, "", True, OPTIONAL_UNION, OPT_OUT_DTO),
        ),
        ("handler", {"return_dto": VetoDTO}, None, User, VETO),
        ("handler", RETURN_DTO, None, STREAM, _cannot("return_dto", HANDLER, False, STREAM, STREAMED)),
        ("handler", DTO, MultipartBody, list[User], _cannot("dto", HANDLER, True, list[User], FORM_ONE)),
        ("handler", DTO, JSON_BODY, Wrapper[User], _cannot("dto", HANDLER, True, Wrapper[User], RETURN_ONLY)),
        (
            "handler",
            RETURN_DTO,
            None,
            Two[User],
            _cannot("return_dto", HANDLER, False, Two[User], MANY.format("'first', 'rest'")),
        ),
        (
            "handler",
            RETURN_DTO,
            None,
            Owned[User],
            _cannot("return_dto", HANDLER, False, Owned[User], MANY.format("'data', 'owner'")),
        ),
        (
            "handler",
            RETURN_DTO,
            None,
            Outer[User],
            _cannot(
                "return_dto",
                HANDLER,
                False,
                Outer[User],
                " The attribute 'inner' holds the model inside another generic type.",
            ),
        ),
    ],
    ids=[
        "handler-data",
        "layer-return",
        "layer-reused",
        "plugin",
        "veto",
        "stream",
        "form-list",
        "data-wrapper",
        "two-attributes",
        "model-attribute",
        "wrapper-attribute",
    ],
)
def test_not_applicable_error(
    placement: Placement, options: dict[str, Any], marker: Any, annotation: Any, message: str
) -> None:
    options = dict(options)
    plugins = options.pop("plugins", ())
    with pytest.raises(DTONotApplicableError) as exc_info:
        if marker is None:
            build_app(placement, method="GET", returns=annotation, plugins=plugins, **options)
        else:
            build_app(
                placement, body=marker[annotation], plugins=plugins, handler_options={"return_dto": None}, **options
            )

    error = exc_info.value
    assert str(error) == f"[paths='/', handler='{'handler' if marker is None else 'handler_with_data'}'] {message}"
    assert isinstance(error, InvalidAnnotationException)
    option = "dto" if marker is not None or message.startswith("'dto=") else "return_dto"
    assert (error.option, error.annotation) == (option, annotation)
    assert error.dto is (VetoDTO if "Veto" in message else UserDTO)


class HookError(DTOFactoryException):
    def __init__(self, message: str, *, code: int) -> None:
        super().__init__(message)
        self.code = code


class HookErrorDTO(DataclassDTO[User]):
    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Any:
        raise HookError("hook failed", code=7)


class RuntimeErrorDTO(DataclassDTO[User]):
    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Any:
        raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("dto", "body", "error", "message"),
    [
        pytest.param(
            UserDTO,
            JSONBody[DTOData[User]],
            MissingDTOError,
            f"The data it receives is annotated 'litestar.dto.data_structures.DTOData[{__name__}.User]', but no DTO "
            "decodes it. Declare 'dto=' on the handler with a DTO that handles the model.",
            id="missing-dto",
        ),
        pytest.param(DataclassDTO[UnionHolder], JSONBody[UnionHolder], DTOTransferTypeError, None, id="transfer"),
        pytest.param(HookErrorDTO, JSONBody[User], HookError, "hook failed", id="third-party"),
        pytest.param(RuntimeErrorDTO, JSONBody[User], RuntimeError, None, id="not-a-dto-error"),
    ],
)
def test_startup_errors_carry_handler_prefix(dto: Any, body: Any, error: type[Exception], message: Any) -> None:
    async def create(data: Any) -> None: ...

    create.__annotations__ = {"data": body, "return": None}
    route_handler = post(["/b", "/a"], name="create-it", dto=None if error is MissingDTOError else dto, return_dto=None)
    with pytest.raises(error) as exc_info:
        Litestar([route_handler(create)], openapi_config=None)

    text = str(exc_info.value)
    if error is RuntimeError:
        assert text == "boom"
        return
    assert type(exc_info.value) is error
    assert text.startswith("[paths='/a,/b', handler='create-it'] ")
    assert text.count("create-it") == 1
    assert "(handler " not in text
    if message is not None:
        assert text.endswith(message)
    if error is DTOTransferTypeError:
        assert "must be tagged" in text
        assert isinstance(exc_info.value.__cause__, TypeError)
    if error is HookError:
        assert exc_info.value.code == 7  # type: ignore[attr-defined]


def test_return_only_dto_rejected_by_msgspec_raises_typed_error_on_schema_generation() -> None:
    @get("/union", return_dto=DataclassDTO[UnionHolder])
    async def read_union() -> UnionHolder:
        return UnionHolder(f=U2(b=1))

    with create_test_client([read_union]) as client:
        assert client.get("/union").json() == {"f": {"b": 1}}
        with pytest.raises(DTOTransferTypeError, match=r"^\[paths='/union', handler='read_union'\] .*must be tagged"):
            client.app.openapi_schema


@pytest.mark.parametrize(
    ("error", "expected_str", "expected_args"),
    [
        (MissingDTOError("x", annotation=None), "[paths='/', handler='h'] x", ("500: [paths='/', handler='h'] x",)),
        (DTOFactoryException("bad"), "[paths='/', handler='h'] bad", ()),
        (DTOFactoryException(), "[paths='/', handler='h']", ()),
        (ImproperlyConfiguredException("bad"), "500: bad", ("500: bad",)),
    ],
    ids=["http-exception", "dto-exception", "empty-detail", "not-a-dto-exception"],
)
def test_wrap_dto_exception(error: Exception, expected_str: str, expected_args: tuple[str, ...]) -> None:
    with pytest.raises(type(error)) as exc_info, HandlerErrorPrefix(handler="h", paths=["/"]).wrap_dto_exception():
        raise error

    assert exc_info.value is error
    assert str(error) == expected_str
    assert error.args == expected_args


class PicklableUserDTO(DataclassDTO[User]):
    pass


@pytest.mark.parametrize("duplicate", [copy.copy, lambda error: pickle.loads(pickle.dumps(error))])
@pytest.mark.parametrize(
    "error",
    [
        MissingDTOError("[paths='/'] no DTO", annotation=DTOData[User]),
        DTONotApplicableError("[paths='/'] bad", dto=PicklableUserDTO, option="dto", annotation=User),
    ],
)
def test_typed_errors(error: DTOFactoryException, duplicate: Callable[[Any], Any]) -> None:
    duplicated = duplicate(error)

    assert type(duplicated) is type(error)
    assert str(duplicated) == str(error)
    assert vars(duplicated) | {"args": None} == vars(error) | {"args": None}
    assert all(issubclass(MissingDTOError, base) for base in (DTOFactoryException, ImproperlyConfiguredException))
    assert issubclass(DTOTransferTypeError, InvalidAnnotationException)
    assert issubclass(DTONotApplicableError, InvalidAnnotationException)


@pytest.mark.parametrize(
    ("returns", "placement", "properties"),
    [
        pytest.param(Optional[Wrapper[User]], "handler", [["data"]], id="optional-wrapper"),
        pytest.param(Optional[Response[User]], "handler", [], id="optional-response"),
        pytest.param(Wrapper[list[User]], "handler", [["data"]], id="wrapper-list"),
        pytest.param(Wrapper[Optional[User]], "handler", [["data"]], id="wrapper-optional"),
        pytest.param(Wrapper[User] | Page[User], "handler", [["data"], ["cursor", "data"]], id="union-of-wrappers"),
        pytest.param(Other, "app", [], id="skipped-layer-dto"),
    ],
)
def test_schema_shows_the_filtered_model(returns: Any, placement: Placement, properties: list[list[str]]) -> None:
    async def read() -> Any: ...

    read.__annotations__ = {"return": returns}
    on_handler = placement == "handler"
    app = Litestar(
        [get("/", return_dto=UserDTO if on_handler else Empty)(read)], return_dto=Empty if on_handler else UserDTO
    )
    schema = app.openapi_schema.to_schema()
    components = schema["components"]["schemas"]
    response = schema["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    members = response.get("oneOf", [response])
    wrappers = [components[member["$ref"].rsplit("/", 1)[1]] for member in members if "$ref" in member]

    assert all("secret" not in component.get("properties", {}) for component in components.values())
    assert [sorted(wrapper["properties"]) for wrapper in wrappers] == properties or not properties
    assert on_handler or not any(name.endswith("ResponseBody") for name in components)


@dataclass
class Bag:
    items: list[int]
    secret: str = "s"

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Any:
        return iter(self.items)

    def __contains__(self, item: object) -> bool:
        return item in self.items


@pytest.mark.parametrize("placement", ["handler", "app"])
def test_collection_like_model_is_the_model(placement: str) -> None:
    received: list[Any] = []
    dto = DataclassDTO[Annotated[Bag, DTOConfig(exclude={"secret"})]]

    async def read() -> Bag:
        return Bag(items=[1, 2], secret="x")

    async def create(data: JSONBody[Bag]) -> None:
        received.append(data)

    on_handler = placement == "handler"
    app = Litestar(
        [get("/", return_dto=dto if on_handler else Empty)(read), post("/", dto=dto if on_handler else Empty)(create)],
        dto=Empty if on_handler else dto,
        return_dto=Empty if on_handler else dto,
    )

    with TestClient(app) as client:
        assert client.get("/").json() == {"items": [1, 2]}
        assert client.post("/", json={"items": [3], "secret": "y"}).status_code == 201
        assert client.get("/schema/openapi.json").status_code == 200
    assert received == [Bag(items=[3], secret="s")]


NewUser = NewType("NewUser", User)
NewerUser = NewType("NewerUser", NewUser)
K = TypeVar("K")


@dataclass
class Tagged(Generic[K, T]):
    tag: K
    item: T


@dataclass
class Keyed(Generic[T]):
    items: dict[str, T]


def _stream(returns: Any, **options: Any) -> Any:
    async def stream() -> AsyncGenerator[Any, None]:
        yield USER

    stream.__annotations__ = {"return": AsyncGenerator[returns, None]}
    return websocket_stream("/ws", **options)(stream)


@pytest.mark.parametrize(
    ("options", "body", "returns"),
    [
        pytest.param(PLUGIN_OPTIONS, None, tuple[User, int], id="plugin-tuple"),
        pytest.param(PLUGIN_OPTIONS, None, User | int, id="plugin-union"),
        pytest.param(PLUGIN_OPTIONS, None, list[User | int], id="plugin-list-of-union"),
        pytest.param(PLUGIN_OPTIONS, None, Iterable[User], id="plugin-iterable"),
        pytest.param(PLUGIN_OPTIONS, None, list[Wrapper[User]], id="plugin-list-of-wrappers"),
        pytest.param(PLUGIN_OPTIONS, None, Wrapper[Wrapper[User]], id="plugin-nested-wrapper"),
        pytest.param(PLUGIN_OPTIONS, None, Response[Wrapper[User]], id="plugin-response-of-wrapper"),
        pytest.param(PLUGIN_OPTIONS, Wrapper[User], None, id="plugin-data-wrapper"),
        pytest.param(PLUGIN_OPTIONS, tuple[User, int], None, id="plugin-data-tuple"),
        pytest.param(PLUGIN_OPTIONS, User | int, None, id="plugin-data-union"),
        pytest.param(DTO, NewUser, None, id="new-type-data"),
        pytest.param(DTO, list[NewUser], None, id="new-type-data-list"),
        pytest.param(DTO, Optional[NewUser], None, id="new-type-data-optional"),
        pytest.param(DTO, Wrapper[NewUser], None, id="new-type-data-wrapper"),
        pytest.param(DTO, NewerUser, None, id="new-type-of-new-type"),
        pytest.param(RETURN_DTO, None, NewUser, id="new-type-return"),
        pytest.param(RETURN_DTO, None, list[NewerUser], id="new-type-return-list"),
        pytest.param(RETURN_DTO, None, Two[User], id="layer-two-attributes"),
        pytest.param(PLUGIN_OPTIONS, None, Tagged[User, User], id="plugin-two-parameters"),
        pytest.param(RETURN_DTO, None, Tagged[User, list[User]], id="layer-model-and-list"),
        pytest.param(PLUGIN_OPTIONS, None, Owned[User], id="plugin-model-attribute"),
        pytest.param(RETURN_DTO, None, Outer[User], id="layer-wrapper-attribute"),
        pytest.param(PLUGIN_OPTIONS, None, Outer[User], id="plugin-wrapper-attribute"),
        pytest.param(PLUGIN_OPTIONS, NewUser, None, id="plugin-new-type-data"),
        pytest.param(PLUGIN_OPTIONS, None, list[NewUser], id="plugin-new-type-return-list"),
        pytest.param(PLUGIN_OPTIONS, None, Wrapper[NewUser], id="plugin-new-type-wrapper"),
        pytest.param(
            {"plugins": (ModelPlugin(User, DataclassDTO[NewUser]),)}, None, NewUser, id="plugin-dto-of-the-new-type"
        ),
    ],
)
def test_dto_mentioned_in_an_unsupported_shape_fails_at_startup(options: Any, body: Any, returns: Any) -> None:
    options = dict(options)
    plugins = options.pop("plugins", ())
    with pytest.raises(DTONotApplicableError) as exc_info:
        if body is None:
            build_app("app", method="GET", returns=returns, plugins=plugins, **options)
        else:
            build_app("app", body=JSON_BODY[body], plugins=plugins, handler_options={"return_dto": None}, **options)
    assert ("serialization plugin" in str(exc_info.value)) is bool(plugins)


@pytest.mark.parametrize(
    ("handler", "options"),
    [
        pytest.param(_listener(NewUser), DTO, id="listener-data"),
        pytest.param(_stream(NewUser), RETURN_DTO, id="stream"),
        pytest.param(_stream(Optional[NewUser]), RETURN_DTO, id="stream-optional"),
    ],
)
def test_new_type_of_the_model_on_a_websocket_fails_at_startup(handler: Any, options: Any) -> None:
    with pytest.raises(DTONotApplicableError):
        Litestar([handler], openapi_config=None, **options)


@pytest.mark.parametrize(
    ("plugin", "returns", "value", "expected"),
    [
        pytest.param(ModelPlugin(Other, UserDTO), Other, OTHER, OTHER_FULL, id="plugin-dto-for-a-model-not-mentioned"),
        pytest.param(PLUGIN[0], Optional[User], USER, USER_ENCODED, id="plugin-optional"),
        pytest.param(PLUGIN[0], Wrapper[User] | None, Wrapper(USER), {"data": USER_ENCODED}, id="plugin-wrapper"),
        pytest.param(PLUGIN[0], UserId, 1, 1, id="plugin-new-type-of-another-type"),
    ],
)
def test_plugin_dto_applies_or_is_skipped(plugin: Any, returns: Any, value: Any, expected: Any) -> None:
    app = build_app("app", method="GET", returns=returns, respond=lambda _: value, plugins=(plugin,))
    with TestClient(app) as client:
        assert client.get("/").json() == expected


@pytest.mark.parametrize(
    ("returns", "value", "expected"),
    [
        pytest.param(Tagged[int, User], Tagged(1, USER), {"tag": 1, "item": USER_ENCODED}, id="model-in-second-param"),
        pytest.param(Tagged[User, int], Tagged(USER, 1), {"tag": USER_ENCODED, "item": 1}, id="model-in-first-param"),
        pytest.param(Keyed[User], Keyed({"k": USER}), {"items": {"k": USER_ENCODED}}, id="mapping-attribute"),
    ],
)
def test_generic_wrapper_transfers_the_attribute_bound_to_the_model(returns: Any, value: Any, expected: Any) -> None:
    app = build_app("handler", method="GET", returns=returns, respond=lambda _: value, return_dto=UserDTO)
    with TestClient(app) as client:
        assert client.get("/").json() == expected
