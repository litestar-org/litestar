import functools
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar, cast

import msgspec
import pytest

from litestar import Litestar, Response, get, post, websocket_listener
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import create_backend
from litestar.handlers import websocket_stream
from litestar.params import JSONBody, MultipartBody, URLEncodedBody
from litestar.testing import RequestFactory, TestClient, create_test_client
from litestar.typing import FieldDefinition
from tests.helpers import not_none
from tests.unit.test_dto import registered

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


EXCLUDE = DTOConfig(exclude={"secret"})
JSON_BODY: Any = JSONBody


@functools.cache
def _pydantic_person() -> tuple[Any, Any]:
    pydantic = pytest.importorskip("pydantic")
    from litestar.plugins.pydantic import PydanticDTO

    person = pydantic.create_model("PYPerson", id=(int, ...), name=(str, ...), secret=(str, "s"))
    return person, PydanticDTO[Annotated[person, EXCLUDE]]


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


def _answers_equal(client: TestClient[Any]) -> Any:
    with_dto = client.get("/dto")
    plain = client.get("/plain")
    assert with_dto.status_code == plain.status_code
    assert with_dto.content == plain.content
    assert with_dto.headers.get("content-type") == plain.headers.get("content-type")
    return with_dto


def test_optional_return_none_matches_handler_without_dto(library: tuple[Any, Any]) -> None:
    model, dto = library
    with create_test_client(_twins(Optional[model], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.status_code == 200
    assert response.json() is None


def test_optional_return_value_is_still_encoded(library: tuple[Any, Any]) -> None:
    model, dto = library
    route_handler = _handler(Optional[model], lambda: model(id=1, name="a", secret="x"), "/dto", return_dto=dto)

    with create_test_client([route_handler]) as client:
        assert client.get("/dto").json() == {"id": 1, "name": "a"}


def test_optional_collection_return_none(library: tuple[Any, Any]) -> None:
    model, dto = library
    with create_test_client(_twins(Optional[list[model]], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.json() is None


def test_response_wrapping_optional_none(library: tuple[Any, Any]) -> None:
    model, dto = library
    with create_test_client(_twins(Response[Optional[model]], lambda: Response(None), dto)) as client:
        response = _answers_equal(client)

    assert response.status_code == 200


def test_optional_generic_wrapper_return_none(library: tuple[Any, Any]) -> None:
    model, dto = library
    with create_test_client(_twins(Optional[Wrapper[model]], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.json() is None


@pytest.mark.parametrize("value", [lambda: None, lambda: Response(None)], ids=["none", "response-none"])
def test_optional_response_wrapping_optional_none(library: tuple[Any, Any], value: Callable[[], Any]) -> None:
    model, dto = library
    with create_test_client(_twins(Optional[Response[Optional[model]]], value, dto)) as client:
        response = _answers_equal(client)

    assert response.status_code == 200


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
    backend = create_backend(
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


def test_optional_body_null_is_none(library: tuple[Any, Any]) -> None:
    model, dto = library
    received: list[Any] = []

    async def create(data: Any = None) -> None:
        received.append(data)

    create.__annotations__ = {"data": JSON_BODY[Optional[model]], "return": None}

    with create_test_client([post("/", dto=dto)(create)]) as client:
        response = client.post("/", content=b"null", headers={"content-type": "application/json"})

    assert response.status_code == 201
    assert received == [None]


def test_optional_body_empty_is_none(library: tuple[Any, Any]) -> None:
    model, dto = library
    received: list[Any] = []

    async def create(data: Any = None) -> None:
        received.append(data)

    create.__annotations__ = {"data": JSON_BODY[Optional[model]], "return": None}

    with create_test_client([post("/", dto=dto)(create)]) as client:
        response = client.post("/")

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


@pytest.mark.parametrize("body", ["json", "urlencoded", "multipart"])
def test_optional_dto_data_body_with_value_is_decoded(body: str) -> None:
    received: list[Any] = []
    marker = {"json": JSONBody, "urlencoded": URLEncodedBody, "multipart": MultipartBody}[body]

    async def create(data: Any = None) -> None:
        received.append(data.create_instance())

    create.__annotations__ = {"data": cast("Any", marker)[Optional[DTOData[DCPerson]]], "return": None}

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


@pytest.mark.parametrize("body", ["urlencoded", "multipart"])
def test_optional_model_form_body_with_value_is_decoded(body: str) -> None:
    received: list[Any] = []
    marker = {"urlencoded": URLEncodedBody, "multipart": MultipartBody}[body]

    async def create(data: Any = None) -> None:
        received.append(data)

    create.__annotations__ = {"data": cast("Any", marker)[Optional[DCPerson]], "return": None}

    with create_test_client([post("/", dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])(create)]) as client:
        if body == "urlencoded":
            response = client.post("/", data={"id": "1", "name": "a"})
        else:
            response = client.post("/", files={"id": (None, "1"), "name": (None, "a")})

    assert response.status_code == 201
    assert received == [DCPerson(id=1, name="a")]
