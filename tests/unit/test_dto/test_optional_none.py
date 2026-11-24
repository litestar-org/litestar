# pyright: reportUnnecessaryTypeIgnoreComment=false

import functools
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar, cast

import msgspec
import pytest

from litestar import Litestar, Response, get, post, websocket_listener
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.handlers import websocket_stream
from litestar.params import JSONBody, MultipartBody, URLEncodedBody
from litestar.testing import RequestFactory, create_test_client
from litestar.typing import FieldDefinition
from tests.helpers import not_none
from tests.unit.test_dto import create_backend_for, registered

T = TypeVar("T")


@dataclass
class DCPerson:
    id: int
    name: str
    secret: str = "s"


class MSPerson(msgspec.Struct):
    id: int
    name: str
    secret: str = "s"


@dataclass
class Wrapper(Generic[T]):
    data: T


@dataclass
class OptionalWrapper(Generic[T]):
    data: Optional[T] = None


EXCLUDE = DTOConfig(exclude={"secret"})
JSON_BODY: Any = JSONBody


@functools.cache
def _pydantic_person() -> tuple[Any, Any]:
    pydantic = pytest.importorskip("pydantic")
    from litestar.plugins.pydantic import PydanticDTO

    person = pydantic.create_model("PYPerson", id=(int, ...), name=(str, ...), secret=(str, "s"))
    pydantic_dto: Any = PydanticDTO
    return person, pydantic_dto[Annotated[person, EXCLUDE]]


@pytest.fixture(params=["dc", "ms", "py"])
def library(request: pytest.FixtureRequest) -> tuple[Any, Any]:
    if request.param == "dc":
        return DCPerson, DataclassDTO[Annotated[DCPerson, EXCLUDE]]
    if request.param == "ms":
        return MSPerson, MsgspecDTO[Annotated[MSPerson, EXCLUDE]]
    return _pydantic_person()


def _handler(returns: Any, value: Callable[[], Any], path: str, **options: Any) -> Any:
    async def handler() -> Any:
        return value()

    handler.__annotations__ = {"return": returns}
    handler.__name__ = path.strip("/").replace("-", "_") or "handler"
    return get(path, **options)(handler)


def _twins(returns: Any, value: Callable[[], Any], dto: type[AbstractDTO[Any]]) -> list[Any]:
    return [
        _handler(returns, value, "/dto", return_dto=dto),
        _handler(returns, value, "/plain", return_dto=None),
    ]


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        pytest.param(lambda m: Optional[m], lambda: None, id="optional"),
        pytest.param(lambda m: Optional[list[m]], lambda: None, id="optional-collection"),  # type: ignore[valid-type]
        pytest.param(lambda m: Response[Optional[m]], lambda: Response(None), id="response-optional"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Wrapper[m]], lambda: None, id="optional-wrapper"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Response[Optional[m]]], lambda: None, id="optional-response"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Response[Optional[m]]], lambda: Response(None), id="optional-response-none"),  # type: ignore[valid-type]
    ],
)
def test_none_return_matches_handler_without_dto(
    library: tuple[Any, Any], annotation: Callable[[Any], Any], value: Callable[[], Any]
) -> None:
    model, dto = library
    with create_test_client(_twins(annotation(model), value, dto)) as client:
        with_dto = client.get("/dto")
        plain = client.get("/plain")

    assert with_dto.status_code == plain.status_code == 200
    assert with_dto.content == plain.content
    assert with_dto.headers.get("content-type") == plain.headers.get("content-type")
    if value() is None:
        assert with_dto.json() is None


def test_optional_return_value_is_encoded(library: tuple[Any, Any]) -> None:
    model, dto = library
    route_handler = _handler(Optional[model], lambda: model(id=1, name="a", secret="x"), "/dto", return_dto=dto)

    with create_test_client([route_handler]) as client:
        assert client.get("/dto").json() == {"id": 1, "name": "a"}


class CopyingBackend(DTOBackend):
    __slots__ = ()

    def __init__(
        self,
        dto_factory: type[AbstractDTO[Any]],
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        inner = DTOBackend(
            dto_factory=dto_factory,
            field_definition=field_definition,
            handler_id=handler_id,
            is_data_field=is_data_field,
            model_type=model_type,
            wrapper_attribute_name=wrapper_attribute_name,
        )
        for name in DTOBackend.__slots__:
            if hasattr(inner, name):
                setattr(self, name, getattr(inner, name))


def test_backend_subclass_skipping_base_constructor_with_optional_annotation() -> None:
    backend = create_backend_for(
        DataclassDTO[Annotated[DCPerson, EXCLUDE]],
        FieldDefinition.from_annotation(Optional[DCPerson]),
        is_data_field=False,
        handler_id="h",
        backend_cls=CopyingBackend,
    )

    assert type(backend) is CopyingBackend
    assert backend.encode_data(None) is None
    assert msgspec.to_builtins(backend.encode_data(DCPerson(id=1, name="a", secret="x"))) == {"id": 1, "name": "a"}


def test_backend_built_without_create_backend_does_not_pass_none() -> None:
    backend = DTOBackend(
        dto_factory=DataclassDTO[DCPerson],
        field_definition=FieldDefinition.from_annotation(Optional[DCPerson]),
        handler_id="h",
        is_data_field=False,
        model_type=DCPerson,
        wrapper_attribute_name=None,
    )

    with pytest.raises(TypeError):
        backend.encode_data(None)


def test_listener_optional_return_none_sends_nothing(library: tuple[Any, Any]) -> None:
    model, dto = library

    async def listener(data: str) -> Any:
        return None if data == "none" else model(id=1, name=data, secret="x")

    listener.__annotations__ = {"data": str, "return": Optional[model]}

    with create_test_client([websocket_listener("/ws", return_dto=dto)(listener)]) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_text("none")
            ws.send_text("a")
            assert ws.receive_json() == {"id": 1, "name": "a"}


def test_stream_optional_item_none_sends_null() -> None:
    @websocket_stream("/ws", return_dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])
    async def stream() -> AsyncGenerator[Optional[DCPerson], None]:
        yield None
        yield DCPerson(id=1, name="a", secret="x")

    with create_test_client([stream]) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_text() == "null"
        assert ws.receive_json() == {"id": 1, "name": "a"}


@pytest.mark.parametrize(
    "request_options",
    [{"content": b"null", "headers": {"content-type": "application/json"}}, {}],
    ids=["null", "empty"],
)
def test_optional_body_null_or_empty_is_none(library: tuple[Any, Any], request_options: dict[str, Any]) -> None:
    model, dto = library
    received: list[Any] = []

    async def create(data: Any = None) -> None:
        received.append(data)

    create.__annotations__ = {"data": JSON_BODY[Optional[model]], "return": None}

    with create_test_client([post("/", dto=dto)(create)]) as client:
        response = client.post("/", **request_options)

    assert response.status_code == 201
    assert received == [None]


def test_optional_dto_data_body_null_is_none() -> None:
    received: list[Any] = []

    @post("/", dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])
    async def create(data: JSONBody[Optional[DTOData[DCPerson]]] = None) -> None:
        received.append(data)

    with create_test_client([create]) as client:
        response = client.post("/", content=b"null", headers={"content-type": "application/json"})

    assert response.status_code == 201
    assert received == [None]


def test_builtins_decoder_returns_none_for_optional_annotation() -> None:
    @post("/", dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])
    async def create(data: URLEncodedBody[Optional[DCPerson]] = None) -> None:
        return None

    app = Litestar([create], openapi_config=None)
    backend = not_none(not_none(registered(app)._dto_plan).data).backend

    assert backend.populate_data_from_builtins(None, RequestFactory().get()) is None


def test_listener_without_dto_returning_none_sends_nothing() -> None:
    @websocket_listener("/ws")
    async def listener(data: str) -> Optional[DCPerson]:
        return None if data == "none" else DCPerson(id=1, name=data)

    with create_test_client([listener]) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("none")
        ws.send_text("a")
        assert ws.receive_json() == {"id": 1, "name": "a", "secret": "s"}


@pytest.mark.parametrize("dto_data", [True, False])
@pytest.mark.parametrize("body", ["json", "urlencoded", "multipart"])
def test_optional_body_with_value_is_decoded(body: str, dto_data: bool) -> None:
    received: list[Any] = []
    marker = {"json": JSONBody, "urlencoded": URLEncodedBody, "multipart": MultipartBody}[body]

    async def create(data: Any = None) -> None:
        received.append(data.create_instance() if dto_data else data)

    inner = DTOData[DCPerson] if dto_data else DCPerson
    create.__annotations__ = {"data": cast("Any", marker)[Optional[inner]], "return": None}

    with create_test_client([post("/", dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])(create)]) as client:
        payload = {"id": 1, "name": "a", "secret": "x"}
        if body == "json":
            response = client.post("/", json=payload)
        elif body == "urlencoded":
            response = client.post("/", data={key: str(value) for key, value in payload.items()})
        else:
            response = client.post("/", files={key: (None, str(value)) for key, value in payload.items()})

    assert response.status_code == 201
    assert received == [DCPerson(id=1, name="a", secret="s")]


PERSON = DCPerson(id=1, name="a")
SENT = {"id": 1, "name": "a", "secret": "x"}
ENCODED = {"id": 1, "name": "a"}


@pytest.mark.parametrize(
    ("annotation", "value", "sent", "expected"),
    [
        pytest.param(Optional[list[DCPerson]], [PERSON], [SENT], [ENCODED], id="optional-list"),
        pytest.param(list[DCPerson] | None, [PERSON], [SENT], [ENCODED], id="list-or-none"),
        pytest.param(Optional[dict[str, DCPerson]], {"k": PERSON}, {"k": SENT}, {"k": ENCODED}, id="optional-dict"),
        pytest.param(Optional[tuple[DCPerson, ...]], (PERSON,), [SENT], [ENCODED], id="optional-tuple"),
        pytest.param(list[Optional[DCPerson]], [None, PERSON], [None, SENT], [None, ENCODED], id="list-of-optional"),
        pytest.param(dict[str, list[DCPerson]], {"k": [PERSON]}, {"k": [SENT]}, {"k": [ENCODED]}, id="dict-of-list"),
        pytest.param(
            dict[str, Optional[DCPerson]],
            {"k": None, "j": PERSON},
            {"k": None, "j": SENT},
            {"k": None, "j": ENCODED},
            id="dict-of-optional",
        ),
        pytest.param(OptionalWrapper[DCPerson], OptionalWrapper(), None, {"data": None}, id="optional-wrapper-none"),
    ],
)
def test_optional_and_nested_collections_round_trip(annotation: Any, value: Any, sent: Any, expected: Any) -> None:
    dto = DataclassDTO[Annotated[DCPerson, EXCLUDE]]
    received: list[Any] = []

    async def read() -> Any:
        return value

    async def create(data: Any) -> None:
        received.append(data)

    read.__annotations__ = {"return": annotation}
    create.__annotations__ = {"data": JSON_BODY[annotation], "return": None}
    route_handlers = [get("/", return_dto=dto)(read)]
    if sent is not None:
        route_handlers.append(post("/", dto=dto)(create))

    with create_test_client(route_handlers) as client:
        response = client.get("/")
        created_status = client.post("/", json=sent).status_code if sent is not None else 201

    assert (response.status_code, response.json()) == (200, expected)
    assert created_status == 201
    assert received == ([value] if sent is not None else [])
