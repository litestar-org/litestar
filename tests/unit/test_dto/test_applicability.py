# pyright: reportUnnecessaryTypeIgnoreComment=false

import json
import sys
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, Optional, Union, cast

import msgspec
import pytest
from typing_extensions import TypeAliasType, TypeVar, TypeVarTuple

from litestar import Controller, Litestar, Response, Router, get, post, websocket_listener
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.dto._plan import resolve_dto_target
from litestar.enums import RequestEncodingType
from litestar.exceptions import DTONotApplicableError, InvalidAnnotationException, MissingDTOError
from litestar.handlers import WebsocketListener, websocket_stream
from litestar.openapi import OpenAPIConfig
from litestar.params import BodyKwarg, FromQuery, JSONBody, MultipartBody, URLEncodedBody
from litestar.plugins import SerializationPlugin
from litestar.response import ServerSentEvent, Stream
from litestar.testing import TestClient, create_test_client
from litestar.types import Empty
from litestar.typing import FieldDefinition
from tests.unit.test_dto import registered

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


UserDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"secret"})]]
OtherDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"hidden"})]]
OtherPluginDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"a"})]]
UserReadDTO = DataclassDTO[Annotated[User, DTOConfig(include={"id"})]]

USER = User(id=1, name="a", secret="x")
USER_IN = {"id": 1, "name": "a", "secret": "x"}
OTHER = Other(a=1, hidden="x")


class ModelPlugin(SerializationPlugin):
    def __init__(self, model: type[Any], dto: type[AbstractDTO[Any]]) -> None:
        self.model = model
        self.dto = dto

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(self.model)

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO[Any]]:
        return self.dto


def _fn(body: Any, returns: Any, respond: Callable[[Any], Any], with_self: bool) -> Any:
    fn: Any
    if body is NO_BODY:
        if with_self:

            async def method(self: Any) -> Any:
                return respond(None)

            fn = method
        else:

            async def handler() -> Any:
                return respond(None)

            fn = handler
        fn.__annotations__ = {"return": returns}
    else:
        if with_self:

            async def method_with_data(self: Any, data: Any) -> Any:
                return respond(data)

            fn = method_with_data
        else:

            async def handler_with_data(data: Any) -> Any:
                return respond(data)

            fn = handler_with_data
        fn.__annotations__ = {"data": body, "return": returns}
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
    openapi_config: OpenAPIConfig | None = None,
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
        controller = type("LayerController", (Controller,), {"path": "/", "handler": route_handler, **options})
        route_handlers = [controller]
        options = {}
    else:
        route_handler = decorator("/", **handler_options)(_fn(body, returns, respond, with_self=False))
        route_handlers = [route_handler]
        if placement == "router":
            route_handlers = [Router("/", route_handlers=route_handlers, **options)]
            options = {}
    return Litestar(route_handlers, plugins=list(plugins), openapi_config=openapi_config, **options)


def describe(data: Any) -> dict[str, Any]:
    return {"type": type(data).__name__, "data": data}


def _target(annotation: Any, direction: Literal["data", "return"]) -> Any:
    target = resolve_dto_target(UserDTO, FieldDefinition.from_annotation(annotation), is_data_field=direction == "data")
    if target is None:
        return None
    wrapped_passes_none = target.wrapper_attribute_name is not None and target.transfer_field.is_optional
    return target.wrapper_attribute_name, target.passes_none, wrapped_passes_none


PLAIN = (None, False, False)
OPTIONAL = (None, True, False)
NOT_APPLICABLE: Any = object()


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
        pytest.param(Response[list[User]], None, ("content", False, False), id="response-list"),
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
        pytest.param(User | Other, None, None, id="union-type"),
        pytest.param(ServerSentEvent, None, None, id="sse"),
        pytest.param(Stream, None, None, id="stream"),
        pytest.param(Any, None, None, id="any"),
        pytest.param(Other, None, None, id="other"),
        pytest.param(None, None, None, id="none"),
        pytest.param(URLEncodedBody[User], PLAIN, NOT_APPLICABLE, id="form-model"),
        pytest.param(
            Annotated[Optional[User], BodyKwarg(media_type=RequestEncodingType.MULTI_PART)],
            OPTIONAL,
            NOT_APPLICABLE,
            id="form-optional",
        ),
        pytest.param(MultipartBody[DTOData[User]], PLAIN, NOT_APPLICABLE, id="form-dto-data"),
        pytest.param(MultipartBody[list[User]], None, NOT_APPLICABLE, id="form-list"),
        pytest.param(URLEncodedBody[dict[str, User]], None, NOT_APPLICABLE, id="form-mapping"),
    ],
)
def test_resolve_dto_target_annotation_table(annotation: Any, data: Any, return_: Any) -> None:
    assert _target(annotation, "data") == data
    if return_ is not NOT_APPLICABLE:
        assert _target(annotation, "return") == return_


def test_resolve_dto_target_of_missing_annotation() -> None:
    assert resolve_dto_target(UserDTO, None, is_data_field=True) is None
    assert resolve_dto_target(UserDTO, FieldDefinition.from_annotation(Empty), is_data_field=False) is None


def respond_described(data: Any) -> dict[str, Any]:
    return describe(data)


DATA_ROWS = [
    pytest.param(
        "handler",
        {"dto": UserDTO},
        JSONBody[User],
        USER_IN,
        (),
        {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}},
        id="handler-dto-applies",
    ),
    pytest.param(
        "handler",
        {"dto": UserDTO},
        JSONBody[Other],
        None,
        (),
        DTONotApplicableError,
        id="handler-dto-for-other-model-raises",
    ),
    pytest.param(
        "handler",
        {"dto": UserDTO},
        NO_BODY,
        None,
        (),
        {"type": "NoneType", "data": None},
        id="handler-dto-without-body",
    ),
    pytest.param(
        "app",
        {"dto": UserDTO},
        JSONBody[User],
        USER_IN,
        (),
        {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}},
        id="layer-dto-applies",
    ),
    pytest.param(
        "app", {"dto": UserDTO}, NO_BODY, None, (), {"type": "NoneType", "data": None}, id="layer-dto-without-body"
    ),
    pytest.param(
        "router",
        {"dto": None},
        JSONBody[User],
        USER_IN,
        (ModelPlugin(User, UserDTO),),
        {"type": "User", "data": USER_IN},
        id="layer-none-disables-plugin",
    ),
    pytest.param(
        "app",
        {},
        JSONBody[User],
        USER_IN,
        (ModelPlugin(User, UserDTO),),
        {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}},
        id="plugin-dto-applies",
    ),
    pytest.param(
        "app",
        {},
        Annotated[tuple[User, int], BodyKwarg(media_type=RequestEncodingType.JSON)],
        [USER_IN, 2],
        (ModelPlugin(User, UserDTO),),
        {"type": "tuple", "data": [USER_IN, 2]},
        id="plugin-dto-skipped-for-tuple",
    ),
    pytest.param("app", {}, JSONBody[User], USER_IN, (), {"type": "User", "data": USER_IN}, id="no-dto"),
    pytest.param("app", {}, JSONBody[DTOData[User]], None, (), MissingDTOError, id="dto-data-without-dto-raises"),
    pytest.param(
        "app", {}, JSON_BODY[Optional[DTOData[User]]], None, (), MissingDTOError, id="optional-dto-data-without-dto"
    ),
    pytest.param(
        "app", {}, JSON_BODY[DTOData[User] | None], None, (), MissingDTOError, id="dto-data-or-none-without-dto"
    ),
    pytest.param(
        "controller",
        {"dto": UserDTO},
        JSONBody[DTOData[Other]],
        None,
        (),
        MissingDTOError,
        id="dto-data-under-skipped-layer-dto-raises",
    ),
]


@pytest.mark.parametrize(("placement", "options", "body", "payload", "plugins", "expected"), DATA_ROWS)
def test_data_direction_rows(
    placement: Placement,
    options: dict[str, Any],
    body: Any,
    payload: Any,
    plugins: tuple[SerializationPlugin, ...],
    expected: Any,
) -> None:
    def build() -> Litestar:
        return build_app(
            placement,
            body=body,
            returns=dict[str, Any],
            respond=respond_described,
            plugins=plugins,
            handler_options={"return_dto": None},
            **options,
        )

    if isinstance(expected, type):
        with pytest.raises(expected):
            build()
        return

    app = build()
    with TestClient(app) as client:
        response = client.post("/", json=payload) if payload is not None else client.post("/")

    assert response.status_code == 201
    assert response.json() == expected


def respond_user(data: Any) -> User:
    return USER


def respond_other(data: Any) -> Other:
    return OTHER


def respond_tuple(data: Any) -> tuple[User, int]:
    return USER, 2


USER_FULL = {"id": 1, "name": "a", "secret": "x"}
USER_ENCODED = {"id": 1, "name": "a"}
OTHER_FULL = {"a": 1, "hidden": "x"}
TUPLE_FULL = [USER_FULL, 2]

RETURN_ROWS = [
    pytest.param(
        "handler", {"return_dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="handler-return-dto-applies"
    ),
    pytest.param(
        "handler",
        {"return_dto": UserDTO},
        {},
        Other,
        respond_other,
        (),
        DTONotApplicableError,
        id="handler-return-dto-for-other-model-raises",
    ),
    pytest.param(
        "handler",
        {"return_dto": UserDTO},
        {},
        ServerSentEvent,
        lambda data: ServerSentEvent("x"),
        (),
        DTONotApplicableError,
        id="handler-return-dto-for-sse-raises",
    ),
    pytest.param(
        "handler",
        {"return_dto": UserDTO},
        {},
        Stream,
        lambda data: Stream(iter([b"x"])),
        (),
        DTONotApplicableError,
        id="handler-return-dto-for-stream-raises",
    ),
    pytest.param(
        "app", {"return_dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="layer-return-dto-applies"
    ),
    pytest.param(
        "app",
        {"return_dto": UserDTO},
        {"dto": OtherDTO},
        Other,
        respond_other,
        (ModelPlugin(Other, OtherPluginDTO),),
        OTHER_FULL,
        id="layer-return-dto-skipped-before-data-dto-and-plugin",
    ),
    pytest.param(
        "router",
        {"return_dto": None},
        {"dto": UserDTO},
        User,
        respond_user,
        (),
        USER_FULL,
        id="layer-none-disables-data-dto-for-return",
    ),
    pytest.param(
        "handler", {"dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="data-dto-reused-for-return"
    ),
    pytest.param(
        "handler",
        {"dto": UserDTO},
        {},
        tuple[User, int],
        respond_tuple,
        (),
        DTONotApplicableError,
        id="data-dto-for-return-tuple-raises",
    ),
    pytest.param(
        "app", {}, {}, Other, respond_other, (ModelPlugin(Other, OtherDTO),), {"a": 1}, id="plugin-dto-for-return"
    ),
    pytest.param(
        "app",
        {},
        {},
        tuple[User, int],
        respond_tuple,
        (ModelPlugin(User, UserDTO),),
        TUPLE_FULL,
        id="plugin-dto-skipped-for-return-tuple",
    ),
    pytest.param(
        "app",
        {},
        {},
        Union[User, Other],
        respond_user,
        (ModelPlugin(User, UserDTO),),
        USER_FULL,
        id="plugin-dto-skipped-for-return-union-without-none",
    ),
    pytest.param("app", {}, {}, User, respond_user, (), USER_FULL, id="no-return-dto"),
]


@pytest.mark.parametrize(
    ("placement", "options", "handler_options", "returns", "respond", "plugins", "expected"), RETURN_ROWS
)
def test_return_direction_rows(
    placement: Placement,
    options: dict[str, Any],
    handler_options: dict[str, Any],
    returns: Any,
    respond: Callable[[Any], Any],
    plugins: tuple[SerializationPlugin, ...],
    expected: Any,
) -> None:
    def build() -> Litestar:
        return build_app(
            placement,
            method="GET",
            returns=returns,
            respond=respond,
            plugins=plugins,
            handler_options=handler_options,
            **options,
        )

    if isinstance(expected, type):
        with pytest.raises(expected):
            build()
        return

    with TestClient(build()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("placement", ["app", "router", "controller"])
def test_layer_data_dto_skipped_for_every_layer_kind(placement: Placement) -> None:
    app = build_app(placement, body=JSONBody[Other], returns=dict[str, Any], respond=respond_described, dto=UserDTO)

    with TestClient(app) as client:
        response = client.post("/", json=OTHER_FULL)

    assert response.status_code == 201
    assert response.json() == {"type": "Other", "data": OTHER_FULL}
    assert registered(app)._dto_plan.data is None


def test_skipped_layer_data_dto_validates_body_without_dto() -> None:
    with_layer_dto = build_app("app", body=JSONBody[Other], returns=None, dto=UserDTO)
    without_dto = build_app("app", body=JSONBody[Other], returns=None)

    with TestClient(with_layer_dto) as client:
        skipped = client.post("/", json={"a": "x"})
    with TestClient(without_dto) as client:
        plain = client.post("/", json={"a": "x"})

    assert skipped.status_code == plain.status_code == 400
    assert skipped.json() == plain.json()


def test_skipped_layer_data_dto_is_reused_for_return() -> None:
    app = build_app("controller", body=JSONBody[Other], returns=list[User], respond=lambda data: [USER], dto=UserDTO)

    with TestClient(app) as client:
        response = client.post("/", json=OTHER_FULL)

    assert response.status_code == 201
    assert response.json() == [USER_ENCODED]
    assert registered(app)._dto_plan.data is None
    assert registered(app).data_dto is UserDTO


def test_skipped_layer_return_dto_does_not_fall_through_to_plugin() -> None:
    app = build_app(
        "app",
        method="GET",
        returns=Other,
        respond=respond_other,
        plugins=(ModelPlugin(Other, OtherDTO),),
        return_dto=UserDTO,
    )

    with TestClient(app) as client:
        assert client.get("/").json() == OTHER_FULL


@pytest.mark.parametrize(
    ("placement", "method", "body"),
    [
        pytest.param("handler", "GET", NO_BODY, id="get"),
        pytest.param("handler", "POST", JSONBody[Other], id="post"),
        pytest.param("controller", "GET", NO_BODY, id="controller"),
    ],
)
def test_declared_dto_beats_serialization_plugin_for_return(placement: Placement, method: Any, body: Any) -> None:
    """The declared DTO encodes the return value ahead of a serialization plugin (issues #3460 and #4906)."""
    app = build_app(
        placement,
        method=method,
        body=body,
        returns=Other,
        respond=respond_other,
        plugins=(ModelPlugin(Other, OtherPluginDTO),),
        dto=OtherDTO,
    )

    with TestClient(app) as client:
        response = client.request(method, "/", json={"a": 1} if body is not NO_BODY else None)

    assert response.json() == {"a": 1}
    assert registered(app, method=method).return_dto is OtherDTO


def test_none_declarations_with_plugin() -> None:
    plugin = ModelPlugin(User, UserDTO)
    no_data_dto = build_app(
        "handler", body=JSONBody[User], returns=User, respond=respond_user, plugins=(plugin,), dto=None
    )
    no_return_dto = build_app(
        "handler", body=JSONBody[User], returns=User, respond=respond_user, plugins=(plugin,), return_dto=None
    )

    with TestClient(no_data_dto) as client:
        assert client.post("/", json=USER_IN).json() == USER_ENCODED
    with TestClient(no_return_dto) as client:
        assert client.post("/", json=USER_IN).json() == USER_FULL

    assert registered(no_data_dto).data_dto is None
    assert registered(no_data_dto).return_dto is UserDTO
    assert registered(no_return_dto).data_dto is UserDTO
    assert registered(no_return_dto).return_dto is None


async def _users() -> AsyncGenerator[User, None]:
    yield USER


@pytest.mark.parametrize(
    ("placement", "options"),
    [
        pytest.param("handler", {"return_dto": UserDTO}, id="handler"),
        pytest.param("app", {"return_dto": UserDTO}, id="layer"),
        pytest.param("handler", {"dto": UserDTO}, id="reused-data-dto"),
    ],
)
def test_async_generator_return(placement: Placement, options: dict[str, Any]) -> None:
    def build() -> Litestar:
        return build_app(
            placement, method="GET", returns=AsyncGenerator[User, None], respond=lambda data: _users(), **options
        )

    with pytest.raises(DTONotApplicableError) as exc_info:
        build()

    assert exc_info.value.option == next(iter(options))
    assert "Streamed items are not transferred by a DTO." in str(exc_info.value)


@pytest.mark.parametrize("returns", [ServerSentEvent, Stream])
def test_server_sent_event_and_stream_returns_start_without_layer_dto(returns: Any) -> None:
    app = build_app("app", method="GET", returns=returns, return_dto=UserDTO)

    assert registered(app, method="GET").return_dto is None


def test_websocket_stream_items_are_encoded() -> None:
    @websocket_stream("/ws", return_dto=UserDTO)
    async def stream() -> AsyncGenerator[User, None]:
        yield USER

    with create_test_client([stream]) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == USER_ENCODED


@pytest.mark.parametrize(
    ("returns", "respond", "expected"),
    [
        pytest.param(Optional[Wrapper[User]], lambda data: Wrapper(USER), {"data": USER_ENCODED}, id="wrapper"),
        pytest.param(Optional[Response[User]], lambda data: Response(USER), USER_ENCODED, id="response"),
    ],
)
def test_optional_generic_wrapper_return_is_encoded(returns: Any, respond: Callable[[Any], Any], expected: Any) -> None:
    app = build_app("handler", method="GET", returns=returns, respond=respond, return_dto=UserDTO)

    with TestClient(app) as client:
        assert client.get("/").json() == expected


def test_union_of_generic_wrappers_over_the_model_is_filtered_and_documented() -> None:
    @get("/", return_dto=UserDTO, sync_to_thread=False)
    def read(kind: FromQuery[str]) -> Wrapper[User] | Page[User]:
        return Wrapper(USER) if kind == "wrapper" else Page(USER)

    app = Litestar([read])
    with TestClient(app) as client:
        assert client.get("/", params={"kind": "wrapper"}).json() == {"data": USER_ENCODED}
        assert client.get("/", params={"kind": "page"}).json() == {"data": USER_ENCODED, "cursor": "c"}

    schema = app.openapi_schema.to_schema()
    response = schema["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    components = schema["components"]["schemas"]
    wrappers = [components[member["$ref"].rsplit("/", 1)[1]] for member in response["oneOf"]]
    assert [sorted(wrapper["properties"]) for wrapper in wrappers] == [["data"], ["cursor", "data"]]
    assert all("secret" not in component.get("properties", {}) for component in components.values())


def test_optional_generic_wrapper_schema_omits_the_excluded_field() -> None:
    @get("/", return_dto=UserDTO, sync_to_thread=False)
    def read() -> Optional[Wrapper[User]]:
        return Wrapper(USER)

    components = Litestar([read]).openapi_schema.to_schema()["components"]["schemas"]

    assert components
    assert all("secret" not in component.get("properties", {}) for component in components.values())


OPTIONAL_UNIONS = {
    "model-first": User | Other | None,
    "model-second": int | User | None,
    "model-and-builtin": User | int | None,
    "list-of-optional-union": list[User | Other | None],
}


@pytest.mark.parametrize(
    ("annotation", "option", "source"),
    [
        *(
            pytest.param(annotation, option, source, id=f"{source}-{option}-{name}")
            for name, annotation in OPTIONAL_UNIONS.items()
            for option in ("dto", "return_dto")
            for source in ("layer", "plugin")
        ),
        pytest.param(list[User] | int | None, "dto", "plugin", id="plugin-dto-list-member"),
        pytest.param(list[User] | int | None, "return_dto", "plugin", id="plugin-return_dto-list-member"),
        pytest.param(Wrapper[User] | int | None, "return_dto", "plugin", id="plugin-return_dto-wrapper-member"),
    ],
)
def test_optional_union_of_several_types_is_not_applicable(annotation: Any, option: str, source: str) -> None:
    options: dict[str, Any] = {option: UserDTO} if source == "layer" else {"plugins": (ModelPlugin(User, UserDTO),)}
    with pytest.raises(DTONotApplicableError) as exc_info:
        if option == "dto":
            build_app("app", body=JSON_BODY[annotation], handler_options={"return_dto": None}, **options)
        else:
            build_app("app", method="GET", returns=annotation, **options)

    assert (exc_info.value.option, exc_info.value.annotation) == (option, annotation)
    if source == "plugin":
        assert "is created by a serialization plugin" in str(exc_info.value)
        assert str(exc_info.value).endswith(f"Declare '{option}=None' on the handler to opt out.")


def test_generic_wrapper_is_not_a_data_shape() -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("handler", body=JSONBody[Wrapper[User]], dto=UserDTO)

    assert exc_info.value.option == "dto"
    assert str(exc_info.value).endswith("A generic wrapper is supported for return values only.")


@pytest.mark.parametrize(
    ("placement", "body"),
    [
        pytest.param("handler", MultipartBody[list[User]], id="multipart-handler"),
        pytest.param("handler", URLEncodedBody[list[User]], id="urlencoded-handler"),
        pytest.param("app", MultipartBody[list[User]], id="multipart-layer"),
    ],
)
def test_form_body_with_collection_annotation_is_not_applicable(placement: Placement, body: Any) -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app(placement, body=body, dto=UserDTO)

    assert "A form body is decoded into one model, not a collection." in str(exc_info.value)


LAYER_SHAPES_WITH_MODEL = [
    pytest.param(tuple[User, int], id="tuple"),
    pytest.param(Union[User, Other], id="union"),
    pytest.param(dict[str, tuple[User, int]], id="mapping-of-tuple"),
]


@pytest.mark.parametrize("option", ["dto", "return_dto"])
@pytest.mark.parametrize("annotation", LAYER_SHAPES_WITH_MODEL)
@pytest.mark.parametrize("placement", ["app", "controller"])
def test_layer_dto_raises_for_annotation_containing_its_model(
    placement: Placement, annotation: Any, option: str
) -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        if option == "dto":
            build_app(placement, body=JSON_BODY[annotation], dto=UserDTO, handler_options={"return_dto": None})
        else:
            build_app(placement, method="GET", returns=annotation, return_dto=UserDTO)

    assert (exc_info.value.option, exc_info.value.annotation) == (option, annotation)
    assert "on a layer" in str(exc_info.value)


@pytest.mark.parametrize("placement", ["handler", "app"])
def test_dto_reused_for_return_raises_for_annotation_containing_its_model(placement: Placement) -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app(placement, method="GET", returns=Union[int, User], respond=respond_user, dto=UserDTO)

    declared = "the handler" if placement == "handler" else "a layer"
    assert str(exc_info.value) == (
        f"[paths='/', handler='handler'] 'dto=DataclassDTO[User]' is declared on {declared}, but cannot encode its "
        f"return value annotated '{Union[int, User]!r}': the DTO handles 'User'. Declare 'return_dto=None' on the "
        "handler to opt out."
    )
    assert (exc_info.value.option, exc_info.value.annotation) == ("dto", Union[int, User])


def test_layer_dto_error_message() -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("app", method="GET", returns=tuple[User, int], return_dto=UserDTO)

    assert str(exc_info.value) == (
        "[paths='/', handler='handler'] 'return_dto=DataclassDTO[User]' is declared on a layer, but cannot encode "
        f"its return value annotated '{tuple[User, int]!r}': the DTO handles 'User'. Declare 'return_dto=None' on "
        "the handler to opt out."
    )


@pytest.mark.parametrize(
    ("returns", "respond", "expected"),
    [
        pytest.param(str, lambda data: "text", b"text", id="str"),
        pytest.param(Other, respond_other, b'{"a":1,"hidden":"x"}', id="other-model"),
        pytest.param(None, lambda data: None, b"null", id="none"),
    ],
)
def test_layer_return_dto_skipped_for_annotation_without_its_model(
    returns: Any, respond: Callable[[Any], Any], expected: Any
) -> None:
    app = build_app("app", method="GET", returns=returns, respond=respond, return_dto=UserDTO)

    with TestClient(app) as client:
        response = client.get("/")

    assert registered(app, method="GET").return_dto is None
    assert response.content == expected


def test_layer_data_dto_skipped_for_str_body() -> None:
    app = build_app("app", body=JSONBody[str], dto=UserDTO, handler_options={"return_dto": None})

    assert registered(app)._dto_plan.data is None


def test_handler_none_opts_out_of_layer_dto_for_annotation_containing_its_model() -> None:
    app = build_app(
        "app",
        method="GET",
        returns=tuple[User, int],
        respond=respond_tuple,
        return_dto=UserDTO,
        handler_options={"return_dto": None},
    )

    with TestClient(app) as client:
        assert client.get("/").json() == TUPLE_FULL


@pytest.mark.parametrize(
    ("placement", "data_type", "sent", "expected"),
    [
        pytest.param("handler", str, None, DTONotApplicableError, id="handler-str"),
        pytest.param("app", str, "text", "text", id="layer-str"),
        pytest.param("handler", User, USER_IN, "User:s", id="handler-model"),
    ],
)
def test_listener_data_dto(placement: Placement, data_type: Any, sent: Any, expected: Any) -> None:
    async def listener(data: Any) -> str:
        return data if isinstance(data, str) else f"{type(data).__name__}:{data.secret}"

    listener.__annotations__ = {"data": data_type, "return": str}
    listener_options: dict[str, Any] = {"dto": UserDTO} if placement == "handler" else {}
    route_handler = websocket_listener("/ws", **listener_options)(listener)
    app_options: dict[str, Any] = {"dto": UserDTO} if placement == "app" else {}

    if isinstance(expected, type):
        with pytest.raises(expected):
            Litestar([route_handler], openapi_config=None, **app_options)
        return

    app = Litestar([route_handler], openapi_config=None, **app_options)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        if isinstance(sent, str):
            ws.send_text(sent)
        else:
            ws.send_json(sent)
        assert ws.receive_text() == expected


class VetoDTO(DataclassDTO[User]):
    @classmethod
    def is_supported_model_type_field(cls, field_definition: FieldDefinition) -> bool:
        return False


@pytest.mark.parametrize("placement", ["handler", "app"])
def test_is_supported_override_vetoes_return_dto(placement: Placement) -> None:
    def build() -> Litestar:
        return build_app(placement, method="GET", returns=User, respond=respond_user, return_dto=VetoDTO)

    if placement == "handler":
        with pytest.raises(DTONotApplicableError) as exc_info:
            build()
        assert str(exc_info.value) == (
            "[paths='/', handler='handler'] 'return_dto=VetoDTO' is declared on the handler, but "
            "VetoDTO.is_supported_model_type_field() declines its return value annotated 'User'."
        )
        return

    app = build()
    with TestClient(app) as client:
        assert client.get("/").json() == USER_FULL
    assert registered(app, method="GET").return_dto is None


@pytest.mark.parametrize(
    ("method", "body", "returns", "options", "expected"),
    [
        pytest.param(
            "POST",
            JSONBody[dict[str, Any]],
            None,
            {"dto": UserDTO},
            ("dto", dict[str, Any], "cannot decode its request body annotated 'dict[str, typing.Any]'"),
            id="data",
        ),
        pytest.param(
            "GET",
            NO_BODY,
            tuple[User, int],
            {"return_dto": UserDTO},
            (
                "return_dto",
                tuple[User, int],
                f"cannot encode its return value annotated '{tuple[User, int]!r}'",
            ),
            id="return",
        ),
    ],
)
def test_dto_not_applicable_error_attributes_and_message(
    method: Any, body: Any, returns: Any, options: dict[str, Any], expected: tuple[Any, ...]
) -> None:
    option, annotation, text = expected

    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("handler", method=method, body=body, returns=returns, **options)

    error = exc_info.value
    assert isinstance(error, InvalidAnnotationException)
    assert error.dto is UserDTO
    assert (error.option, error.annotation) == (option, annotation)
    assert str(error) == (
        f"[paths='/', handler='{'handler_with_data' if body is not NO_BODY else 'handler'}'] "
        f"'{option}=DataclassDTO[User]' is declared on the handler, but {text}: the DTO handles 'User'."
    )


def test_skipped_layer_dto_openapi_documents_plain_model() -> None:
    @post("/")
    async def create(data: JSONBody[Other]) -> None:
        return None

    app = Litestar([create], dto=UserDTO)
    schema = app.openapi_schema.to_schema()

    reference = schema["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert reference.rsplit("/", 1)[-1].endswith("Other")
    assert "RequestBody" not in reference


@pytest.mark.parametrize(
    ("returns", "respond"),
    [
        pytest.param(None, lambda data: None, id="none"),
        pytest.param(Any, respond_user, id="any"),
    ],
)
def test_handler_return_dto_that_does_not_apply_raises(returns: Any, respond: Callable[[Any], Any]) -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("handler", method="GET", returns=returns, respond=respond, return_dto=UserDTO)

    error = exc_info.value
    assert (error.dto, error.option) == (UserDTO, "return_dto")
    assert "cannot encode its return value annotated" in str(error)


def test_handler_dto_used_for_data_only_starts() -> None:
    app = build_app("handler", body=JSONBody[User], returns=None, dto=UserDTO)

    with TestClient(app) as client:
        assert client.post("/", json=USER_IN).status_code == 201


def test_handler_dto_without_request_data_under_layer_return_dto_starts() -> None:
    @get("/", dto=UserDTO)
    async def read() -> User:
        return USER

    app = Litestar([Router("/", route_handlers=[read], return_dto=UserReadDTO)], openapi_config=None)

    with TestClient(app) as client:
        assert client.get("/").json() == {"id": 1}
    assert registered(app, method="GET").return_dto is UserReadDTO


def test_generated_options_handler_starts_with_app_level_dtos() -> None:
    app = build_app("app", method="GET", returns=User, respond=respond_user, dto=UserDTO, return_dto=UserDTO)

    with TestClient(app) as client:
        assert client.options("/").status_code == 204


def test_listener_class_return_dto_that_does_not_apply_raises() -> None:
    class Listener(WebsocketListener):
        path = "/ws"
        return_dto = UserDTO

        async def on_receive(self, data: str) -> None:
            return None

    with pytest.raises(DTONotApplicableError, match=r"cannot encode its return value annotated 'None'"):
        Litestar([Listener], openapi_config=None)


@pytest.mark.parametrize(
    ("placement", "method", "body", "returns", "option"),
    [
        pytest.param("handler", "GET", NO_BODY, dict, "return_dto", id="handler-return-dict"),
        pytest.param("handler", "GET", NO_BODY, list, "return_dto", id="handler-return-list"),
        pytest.param("handler", "POST", JSONBody[dict], None, "dto", id="handler-body-dict"),
        pytest.param("app", "GET", NO_BODY, dict, "return_dto", id="layer-return-dict"),
        pytest.param("app", "GET", NO_BODY, list, "return_dto", id="layer-return-list"),
        pytest.param("app", "POST", JSONBody[dict], None, "dto", id="layer-body-dict"),
        *(
            pytest.param(placement, method, body, returns, option, id=f"{placement}-{name}")
            for placement in ("handler", "app")
            for name, method, body, returns, option in (
                ("return-list-of-dict", "GET", NO_BODY, list[dict], "return_dto"),
                ("return-dict-of-list", "GET", NO_BODY, dict[str, list], "return_dto"),
                ("return-tuple-of-dict", "GET", NO_BODY, tuple[dict, ...], "return_dto"),
                ("return-optional-list-of-dict", "GET", NO_BODY, Optional[list[dict]], "return_dto"),
                ("body-list-of-dict", "POST", JSONBody[list[dict]], None, "dto"),
                ("body-list-of-dto-data", "POST", JSONBody[list[DTOData]], None, "dto"),
            )
        ),
        pytest.param("handler", "POST", URLEncodedBody[DTOData], None, "dto", id="handler-form-body-dto-data"),
    ],
)
def test_bare_collection_annotation_is_not_applicable(
    placement: Placement, method: Any, body: Any, returns: Any, option: str
) -> None:
    options: dict[str, Any] = {option: UserDTO}

    def build() -> Litestar:
        return build_app(
            placement, method=method, body=body, returns=returns, respond=lambda data: returns(), **options
        )

    if placement == "handler":
        with pytest.raises(DTONotApplicableError, match=r"^\[paths='/', handler='\w+'\] "):
            build()
        return

    app = build()
    plan = registered(app, method=method)._dto_plan
    assert plan.data is None
    assert plan.return_ is None


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


@pytest.mark.parametrize(
    ("listener", "expected"), [(InheritingTextListener, "text"), (InheritingUserListener, '{"id":1,"name":"a"}')]
)
def test_listener_return_dto_inherited_from_base_class(listener: type[WebsocketListener], expected: str) -> None:
    with create_test_client([listener]) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("text")
        assert ws.receive_text() == expected


def test_listener_return_dto_in_own_class_body_must_apply() -> None:
    with pytest.raises(DTONotApplicableError, match=r"cannot encode its return value annotated 'str'"):
        Litestar([OwnTextListener], openapi_config=None)


class CollectionMethods:
    items: list[int]

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Any:
        return iter(self.items)

    def __contains__(self, item: object) -> bool:
        return item in self.items


@dataclass
class DataclassBag(CollectionMethods):
    items: list[int]
    secret: str = "s"


class StructBag(msgspec.Struct):
    items: list[int]
    secret: str = "s"

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Any:
        return iter(self.items)

    def __contains__(self, item: object) -> bool:
        return item in self.items


def assert_collection_like_model_round_trips(model: Any, dto: type[AbstractDTO[Any]], placement: Placement) -> None:
    received: list[Any] = []

    async def read() -> Any:
        return model(items=[1, 2], secret="x")

    async def create(data: Any) -> None:
        received.append(data)

    read.__annotations__ = {"return": model}
    create.__annotations__ = {"data": cast("Any", JSONBody)[model], "return": None}
    read_options: dict[str, Any] = {"return_dto": dto} if placement == "handler" else {}
    create_options: dict[str, Any] = {"dto": dto} if placement == "handler" else {}
    app_options: dict[str, Any] = {"dto": dto, "return_dto": dto} if placement == "app" else {}
    app = Litestar([get("/", **read_options)(read), post("/", **create_options)(create)], **app_options)

    with TestClient(app) as client:
        read_response = client.get("/")
        create_response = client.post("/", json={"items": [3], "secret": "y"})
        schema_response = client.get("/schema/openapi.json")

    assert read_response.json() == {"items": [1, 2]}
    assert create_response.status_code == 201
    assert received == [model(items=[3], secret="s")]
    assert schema_response.status_code == 200


@pytest.mark.parametrize("placement", ["handler", "app"])
@pytest.mark.parametrize(
    ("model", "dto"),
    [
        pytest.param(
            DataclassBag, DataclassDTO[Annotated[DataclassBag, DTOConfig(exclude={"secret"})]], id="dataclass"
        ),
        pytest.param(StructBag, MsgspecDTO[Annotated[StructBag, DTOConfig(exclude={"secret"})]], id="msgspec"),
    ],
)
def test_collection_like_model_is_the_model(model: Any, dto: type[AbstractDTO[Any]], placement: Placement) -> None:
    assert_collection_like_model_round_trips(model, dto, placement)


UserAlias = TypeAliasType("UserAlias", User)
UsersAlias = TypeAliasType("UsersAlias", list[User])
UserAliasAlias = TypeAliasType("UserAliasAlias", UserAlias)
OptionalUserAlias = TypeAliasType("OptionalUserAlias", Optional[User])
ForwardAlias = TypeAliasType("ForwardAlias", list["User"])
StringPageAlias = TypeAliasType("StringPageAlias", "list[T]", type_params=(T,))
PageAlias = TypeAliasType("PageAlias", list[T], type_params=(T,))
IdentAlias = TypeAliasType("IdentAlias", T, type_params=(T,))
D = TypeVar("D", default=User)
DefaultPageAlias = TypeAliasType("DefaultPageAlias", list[D], type_params=(D,))
Ts = TypeVarTuple("Ts")
TupleAlias = TypeAliasType("TupleAlias", tuple[*Ts], type_params=(Ts,))
Json = TypeAliasType("Json", Union[dict[str, "Json"], list["Json"], str, int, None])  # type: ignore[misc]
NEEDS_TYPE_STATEMENT = pytest.mark.skipif(sys.version_info < (3, 12), reason="type keyword needs 3.12")
NEEDS_TYPE_PARAMETER_DEFAULTS = pytest.mark.skipif(sys.version_info < (3, 13), reason="defaults need 3.13")


def type_statement(source: str) -> Any:
    namespace: dict[str, Any] = {"User": User}
    exec(source, namespace)
    return namespace["Alias"]


ALIAS_ROWS = [
    pytest.param("app", "data", lambda: UserAlias, User, USER_IN, id="data-alias"),
    pytest.param("handler", "data", lambda: UsersAlias, list[User], [USER_IN], id="data-alias-of-list"),
    pytest.param("app", "data", lambda: OptionalUserAlias, Optional[User], USER_IN, id="data-alias-of-optional"),
    pytest.param("app", "data", lambda: PageAlias[User], list[User], [USER_IN], id="data-generic-alias"),
    pytest.param(
        "app",
        "return",
        lambda: type_statement("type Alias = User"),
        User,
        USER,
        id="return-type-statement",
        marks=NEEDS_TYPE_STATEMENT,
    ),
    pytest.param("app", "return", lambda: list[UserAlias], list[User], [USER], id="return-list-of-alias"),
    pytest.param("app", "return", lambda: Optional[UserAlias], Optional[User], USER, id="return-optional-alias"),
    pytest.param(
        "handler", "return", lambda: Response[UsersAlias], Response[list[User]], Response([USER]), id="return-response"
    ),
    pytest.param("app", "return", lambda: Wrapper[UserAlias], Wrapper[User], Wrapper(USER), id="return-wrapper"),
    pytest.param("app", "return", lambda: UserAliasAlias, User, USER, id="return-alias-of-alias"),
    pytest.param("app", "return", lambda: ForwardAlias, list[User], [USER], id="return-forward-reference"),
    pytest.param(
        "app",
        "return",
        lambda: TypeAliasType("Alias", list["HiddenUser"]),  # type: ignore[name-defined]  # noqa: F821
        list[User],
        [USER],
        id="return-forward-reference-in-signature-namespace",
    ),
    pytest.param("app", "data", lambda: IdentAlias[IdentAlias[User]], User, USER_IN, id="data-generic-alias-in-itself"),
    pytest.param("app", "return", lambda: DefaultPageAlias, list[User], [USER], id="return-bare-alias-with-defaults"),
    pytest.param("app", "return", lambda: StringPageAlias[User], list[User], [USER], id="return-generic-string-alias"),
    pytest.param(
        "app",
        "reused",
        lambda: list[StringPageAlias[User]],
        list[list[User]],
        [[USER]],
        id="return-alias-with-reused-dto",
    ),
]


@pytest.mark.parametrize(("placement", "direction", "alias", "plain", "sent"), ALIAS_ROWS)
def test_type_alias_applies_like_its_value(
    placement: Placement, direction: str, alias: Callable[[], Any], plain: Any, sent: Any
) -> None:
    def observe(annotation: Any) -> tuple[int, str, str]:
        if direction == "data":
            app = build_app(
                placement,
                body=JSON_BODY[annotation],
                returns=dict[str, Any],
                respond=respond_described,
                handler_options={"return_dto": None},
                openapi_config=DEFAULT_OPENAPI_CONFIG,
                signature_namespace={"HiddenUser": User},
                dto=UserDTO,
            )
        else:
            app = build_app(
                placement,
                method="GET",
                returns=annotation,
                respond=lambda data: sent,
                openapi_config=DEFAULT_OPENAPI_CONFIG,
                signature_namespace={"HiddenUser": User, "User": Other},
                **{"dto" if direction == "reused" else "return_dto": UserDTO},  # type: ignore[arg-type]
            )
        with TestClient(app) as client:
            response = client.post("/", json=sent) if direction == "data" else client.get("/")
        return response.status_code, response.text, json.dumps(app.openapi_schema.to_schema())

    observed = observe(alias())

    assert observed == observe(plain)
    assert '"secret":"x"' not in observed[1]
    assert "secret" not in observed[2]


def test_plugin_dto_applies_through_a_type_alias_and_skips_an_unresolvable_one() -> None:
    plugins = (ModelPlugin(User, UserDTO),)
    app = build_app("app", method="GET", returns=UsersAlias, respond=lambda data: [USER], plugins=plugins)

    with TestClient(app) as client:
        assert client.get("/").json() == [USER_ENCODED]

    Alias = TypeAliasType("Alias", list["Missing"])  # type: ignore[name-defined]  # noqa: F821
    assert build_app("app", method="GET", returns=Alias, respond=lambda data: [], plugins=plugins)


@pytest.mark.parametrize("body", [URLEncodedBody, MultipartBody])
def test_empty_form_body_passes_none_through_an_optional_alias(body: Any) -> None:
    def observe(annotation: Any) -> tuple[int, Any]:
        app = build_app(
            "handler",
            body=body[annotation],
            returns=dict[str, Any],
            respond=respond_described,
            handler_options={"return_dto": None},
            dto=UserDTO,
        )
        with TestClient(app) as client:
            response = client.post("/")
        return response.status_code, response.json()

    assert observe(OptionalUserAlias) == observe(Optional[User]) == (201, {"type": "NoneType", "data": None})


@pytest.mark.parametrize(
    ("option", "alias", "reason"),
    [
        pytest.param(
            "dto",
            lambda: type_statement("type Alias = list[Missing]"),
            "name 'Missing' is not defined",
            id="name-error",
            marks=NEEDS_TYPE_STATEMENT,
        ),
        pytest.param(
            "return_dto",
            lambda: TypeAliasType("Alias", list["Missing"]),  # type: ignore[name-defined]  # noqa: F821
            "name 'Missing' is not defined",
            id="forward-reference",
        ),
        pytest.param("return_dto", lambda: PageAlias, "type parameters", id="bare-generic-alias"),
        pytest.param(
            "return_dto",
            lambda: TypeAliasType("Alias", list["1/0"]),  # type: ignore[valid-type]
            "division by zero",
            id="forward-reference-error",
        ),
        pytest.param("return_dto", lambda: TupleAlias[User, int], "type parameters", id="type-var-tuple"),
        pytest.param(
            "return_dto",
            lambda: type_statement("type Alias = dict[str, list['User'] | 'Other']"),
            "unsupported operand",
            id="value-error",
            marks=NEEDS_TYPE_STATEMENT,
        ),
        pytest.param(
            "return_dto",
            lambda: type_statement("type Alias[X = Missing] = list[X]"),
            "name 'Missing' is not defined",
            id="type-parameter-default-error",
            marks=NEEDS_TYPE_PARAMETER_DEFAULTS,
        ),
    ],
)
def test_unresolvable_type_alias_fails_at_startup(option: str, alias: Callable[[], Any], reason: str) -> None:
    pattern = rf"^\[paths='/', handler='handler\w*'\] Cannot resolve the type alias '.+': .*{reason}"

    with pytest.raises(InvalidAnnotationException, match=pattern):
        if option == "dto":
            build_app("app", body=JSON_BODY[alias()], dto=UserDTO, handler_options={"return_dto": None})
        else:
            build_app("app", method="GET", returns=alias(), return_dto=UserDTO, signature_namespace={"T": T})


@pytest.mark.parametrize(
    "alias",
    [
        pytest.param(lambda: Json, id="typing_extensions"),
        pytest.param(
            lambda: type_statement("type Alias = dict[str, Alias] | list[Alias] | str | int | None"),
            id="type-statement",
            marks=NEEDS_TYPE_STATEMENT,
        ),
    ],
)
def test_recursive_type_alias_without_the_model_starts_under_layer_dto(alias: Callable[[], Any]) -> None:
    app = build_app("app", method="GET", returns=alias(), respond=lambda data: {"a": [1]}, dto=UserDTO)

    with TestClient(app) as client:
        assert client.get("/").json() == {"a": [1]}
