from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, Optional, TypeVar, Union

import pytest

from litestar import Controller, Litestar, Response, Router, get, post, websocket_listener
from litestar.datastructures import UploadFile
from litestar.di._helpers import _format_key
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData
from litestar.dto._plan import resolve_dto_target
from litestar.enums import RequestEncodingType
from litestar.exceptions import DTONotApplicableError, InvalidAnnotationException, MissingDTOError
from litestar.handlers import websocket_stream
from litestar.params import BodyKwarg, JSONBody, MultipartBody, URLEncodedBody
from litestar.plugins import SerializationPlugin
from litestar.response import ServerSentEvent, Stream
from litestar.testing import TestClient, create_test_client
from litestar.types import Empty
from litestar.typing import FieldDefinition

T = TypeVar("T")

Placement = Literal["handler", "controller", "router", "app"]
NO_BODY: Any = object()


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


UserDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"secret"})]]
OtherDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"hidden"})]]
OtherPluginDTO = DataclassDTO[Annotated[Other, DTOConfig(exclude={"a"})]]

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
    return Litestar(route_handlers, plugins=list(plugins), openapi_config=None, **options)


def registered(app: Litestar, method: Any = "POST") -> Any:
    return app.route_handler_method_map["/"][method]


def describe(data: Any) -> dict[str, Any]:
    return {"type": type(data).__name__, "data": data}


def _target(annotation: Any, direction: Literal["data", "return"]) -> Any:
    target = resolve_dto_target(UserDTO, FieldDefinition.from_annotation(annotation), direction)
    if target is None:
        return None
    return target.wrapper_attribute_name, target.passes_none, target.wrapped_passes_none


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
        pytest.param(User | Other | None, OPTIONAL, OPTIONAL, id="optional-union-model-first"),
        pytest.param(Other | User | None, None, None, id="optional-union-other-first"),
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
    assert resolve_dto_target(UserDTO, None, "data") is None
    assert resolve_dto_target(UserDTO, FieldDefinition.from_annotation(Empty), "return") is None


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
        id="AD1",
    ),
    pytest.param("handler", {"dto": UserDTO}, JSONBody[Other], None, (), DTONotApplicableError, id="AD2"),
    pytest.param("handler", {"dto": UserDTO}, NO_BODY, None, (), {"type": "NoneType", "data": None}, id="AD3"),
    pytest.param(
        "app",
        {"dto": UserDTO},
        JSONBody[User],
        USER_IN,
        (),
        {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}},
        id="AD4",
    ),
    pytest.param(
        "app",
        {"dto": UserDTO},
        JSONBody[Other],
        {"a": 1, "hidden": "x"},
        (),
        {"type": "Other", "data": {"a": 1, "hidden": "x"}},
        id="AD5",
    ),
    pytest.param("app", {"dto": UserDTO}, NO_BODY, None, (), {"type": "NoneType", "data": None}, id="AD6"),
    pytest.param(
        "router",
        {"dto": None},
        JSONBody[User],
        USER_IN,
        (ModelPlugin(User, UserDTO),),
        {"type": "User", "data": USER_IN},
        id="AD7",
    ),
    pytest.param(
        "app",
        {},
        JSONBody[User],
        USER_IN,
        (ModelPlugin(User, UserDTO),),
        {"type": "User", "data": {"id": 1, "name": "a", "secret": "s"}},
        id="AD8",
    ),
    pytest.param(
        "app",
        {},
        Annotated[tuple[User, int], BodyKwarg(media_type=RequestEncodingType.JSON)],
        [USER_IN, 2],
        (ModelPlugin(User, UserDTO),),
        {"type": "tuple", "data": [USER_IN, 2]},
        id="AD9",
    ),
    pytest.param("app", {}, JSONBody[User], USER_IN, (), {"type": "User", "data": USER_IN}, id="AD10"),
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
    pytest.param("handler", {"return_dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="AR1"),
    pytest.param(
        "handler", {"return_dto": UserDTO}, {}, tuple[User, int], respond_tuple, (), DTONotApplicableError, id="AR2"
    ),
    pytest.param("handler", {"return_dto": UserDTO}, {}, Other, respond_other, (), OTHER_FULL, id="AR3"),
    pytest.param("app", {"return_dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="AR4"),
    pytest.param("app", {"return_dto": UserDTO}, {}, tuple[User, int], respond_tuple, (), TUPLE_FULL, id="AR5"),
    pytest.param(
        "app",
        {"return_dto": UserDTO},
        {"dto": OtherDTO},
        Other,
        respond_other,
        (ModelPlugin(Other, OtherPluginDTO),),
        OTHER_FULL,
        id="AR6",
    ),
    pytest.param("router", {"return_dto": None}, {"dto": UserDTO}, User, respond_user, (), USER_FULL, id="AR7"),
    pytest.param("handler", {"dto": UserDTO}, {}, User, respond_user, (), USER_ENCODED, id="AR8"),
    pytest.param("handler", {"dto": UserDTO}, {}, tuple[User, int], respond_tuple, (), TUPLE_FULL, id="AR9"),
    pytest.param("app", {}, {}, Other, respond_other, (ModelPlugin(Other, OtherDTO),), {"a": 1}, id="AR10"),
    pytest.param("app", {}, {}, tuple[User, int], respond_tuple, (ModelPlugin(User, UserDTO),), TUPLE_FULL, id="AR11"),
    pytest.param("app", {}, {}, User, respond_user, (), USER_FULL, id="AR12"),
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


def test_skipped_layer_data_dto_is_still_reused_for_return() -> None:
    app = build_app("controller", body=JSONBody[Other], returns=list[User], respond=lambda data: [USER], dto=UserDTO)

    with TestClient(app) as client:
        response = client.post("/", json=OTHER_FULL)

    assert response.status_code == 201
    assert response.json() == [USER_ENCODED]
    assert registered(app)._dto_plan.data is None
    assert registered(app).data_dto is UserDTO


def test_skipped_layer_dto_with_dto_data_raises_missing_dto_error() -> None:
    with pytest.raises(MissingDTOError):
        build_app("controller", body=JSONBody[DTOData[Other]], dto=UserDTO)


def test_skipped_layer_return_dto_does_not_fall_through_to_data_dto() -> None:
    app = build_app(
        "app",
        body=JSONBody[Other],
        returns=Other,
        respond=lambda data: Other(a=data.a + 1, hidden="kept"),
        handler_options={"dto": OtherDTO},
        return_dto=UserDTO,
    )

    with TestClient(app) as client:
        response = client.post("/", json={"a": 1, "hidden": "ignored"})

    assert response.status_code == 201
    assert response.json() == {"a": 2, "hidden": "kept"}


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
    assert registered(app, method).return_dto is OtherDTO


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

    if placement == "handler" and "return_dto" in options:
        with pytest.raises(DTONotApplicableError) as exc_info:
            build()
        assert exc_info.value.direction == "return"
        assert str(exc_info.value).endswith("Streamed items are not transferred by a DTO.")
        return

    assert registered(build(), "GET").return_dto is None


@pytest.mark.parametrize("returns", [ServerSentEvent, Stream])
@pytest.mark.parametrize("placement", ["handler", "app"])
def test_server_sent_event_and_stream_returns_start_without_dto(placement: Placement, returns: Any) -> None:
    app = build_app(placement, method="GET", returns=returns, return_dto=UserDTO)

    assert registered(app, "GET").return_dto is None


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


@pytest.mark.parametrize(
    ("placement", "returns", "expected"),
    [
        pytest.param("app", User | Other | None, USER_ENCODED, id="model-first-layer"),
        pytest.param("handler", User | Other | None, USER_ENCODED, id="model-first-handler"),
        pytest.param("app", Other | User | None, USER_FULL, id="other-first-layer"),
    ],
)
def test_optional_union_resolves_to_first_member_like_baseline(
    placement: Placement, returns: Any, expected: Any
) -> None:
    app = build_app(placement, method="GET", returns=returns, respond=respond_user, return_dto=UserDTO)

    with TestClient(app) as client:
        assert client.get("/").json() == expected


def test_generic_wrapper_is_not_a_data_shape() -> None:
    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("handler", body=JSONBody[Wrapper[User]], dto=UserDTO)

    assert exc_info.value.direction == "data"
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
    if placement == "handler":
        with pytest.raises(DTONotApplicableError) as exc_info:
            build_app(placement, body=body, dto=UserDTO)
        assert str(exc_info.value).endswith("A form body is decoded into one model, not a collection.")
        return

    app = build_app(placement, body=body, dto=UserDTO)

    assert registered(app)._dto_plan.data is None


def test_layer_dto_with_upload_file_body_is_skipped() -> None:
    app = build_app(
        "app",
        body=MultipartBody[list[UploadFile]],
        returns=list[str],
        respond=lambda data: [upload.filename for upload in data],
        dto=UserDTO,
    )

    with TestClient(app) as client:
        response = client.post("/", files=[("file", ("a.txt", b"a")), ("file", ("b.txt", b"b"))])

    assert response.status_code == 201
    assert response.json() == ["a.txt", "b.txt"]


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


def test_is_supported_override_vetoes_return_dto() -> None:
    app = build_app("handler", method="GET", returns=User, respond=respond_user, return_dto=VetoDTO)

    with TestClient(app) as client:
        assert client.get("/").json() == USER_FULL
    assert registered(app, "GET").return_dto is None


@pytest.mark.parametrize(
    ("method", "body", "returns", "options", "expected"),
    [
        pytest.param(
            "POST",
            JSONBody[dict[str, Any]],
            None,
            {"dto": UserDTO},
            ("dto", "data", dict[str, Any], "cannot decode its request body annotated 'dict[str, typing.Any]'"),
            id="data",
        ),
        pytest.param(
            "GET",
            NO_BODY,
            tuple[User, int],
            {"return_dto": UserDTO},
            (
                "return_dto",
                "return",
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
    option, direction, annotation, text = expected

    with pytest.raises(DTONotApplicableError) as exc_info:
        build_app("handler", method=method, body=body, returns=returns, **options)

    error = exc_info.value
    assert isinstance(error, InvalidAnnotationException)
    assert error.dto is UserDTO
    assert (error.option, error.direction, error.annotation) == (option, direction, annotation)
    assert str(error) == (
        f"[paths='/', handler='{'handler_with_data' if body is not NO_BODY else 'handler'}'] "
        f"'{option}={_format_key(UserDTO)}' is declared on the handler, but {text}: the DTO handles 'User'."
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
