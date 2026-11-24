from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar

import msgspec
import pydantic
import pytest

from litestar import Litestar, Response, get, post, websocket_listener
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import create_backend
from litestar.handlers import websocket_stream
from litestar.params import JSONBody, URLEncodedBody
from litestar.plugins.pydantic import PydanticDTO
from litestar.testing import RequestFactory, TestClient, create_test_client
from litestar.typing import FieldDefinition
from tests.helpers import not_none

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


class PYPerson(pydantic.BaseModel):
    id: int
    name: str
    secret: str = "s"


@dataclass
class Wrapper(Generic[T]):
    data: T


EXCLUDE = DTOConfig(exclude={"secret"})
JSON_BODY: Any = JSONBody
LIBRARIES = [
    pytest.param(DCPerson, DataclassDTO[Annotated[DCPerson, EXCLUDE]], id="dc"),
    pytest.param(MSPerson, MsgspecDTO[Annotated[MSPerson, EXCLUDE]], id="ms"),
    pytest.param(PYPerson, PydanticDTO[Annotated[PYPerson, EXCLUDE]], id="py"),
]


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


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_return_none_matches_handler_without_dto(model: Any, dto: Any) -> None:
    with create_test_client(_twins(Optional[model], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_return_value_is_still_encoded(model: Any, dto: Any) -> None:
    route_handler = _handler(Optional[model], lambda: model(id=1, name="a", secret="x"), "/dto", return_dto=dto)

    with create_test_client([route_handler]) as client:
        assert client.get("/dto").json() == {"id": 1, "name": "a"}


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_collection_return_none(model: Any, dto: Any) -> None:
    with create_test_client(_twins(Optional[list[model]], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.json() is None


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_response_wrapping_optional_none(model: Any, dto: Any) -> None:
    with create_test_client(_twins(Response[Optional[model]], lambda: Response(None), dto)) as client:
        response = _answers_equal(client)

    assert response.status_code == 200


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_generic_wrapper_return_none(model: Any, dto: Any) -> None:
    with create_test_client(_twins(Optional[Wrapper[model]], lambda: None, dto)) as client:
        response = _answers_equal(client)

    assert response.json() is None


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_non_optional_return_none_is_unchanged(model: Any, dto: Any) -> None:
    route_handler = _handler(model, lambda: None, "/dto", return_dto=dto)

    with create_test_client([route_handler], raise_server_exceptions=False) as client:
        assert client.get("/dto").status_code == 500


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_non_optional_wrapped_none_is_unchanged(model: Any, dto: Any) -> None:
    route_handler = _handler(Response[model], lambda: Response(None), "/dto", return_dto=dto)

    with create_test_client([route_handler], raise_server_exceptions=False) as client:
        assert client.get("/dto").status_code == 500


@pytest.mark.parametrize("value", [lambda: None, lambda: Response(None)], ids=["none", "response-none"])
@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_response_wrapping_optional_none(model: Any, dto: Any, value: Callable[[], Any]) -> None:
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


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_listener_optional_return_none_sends_nothing(model: Any, dto: Any) -> None:
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


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_body_null_is_none(model: Any, dto: Any) -> None:
    received: list[Any] = []

    async def create(data: Any = None) -> None:
        received.append(data)

    create.__annotations__ = {"data": JSON_BODY[Optional[model]], "return": None}

    with create_test_client([post("/", dto=dto)(create)]) as client:
        response = client.post("/", content=b"null", headers={"content-type": "application/json"})

    assert response.status_code == 201
    assert received == [None]


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_optional_body_empty_is_none(model: Any, dto: Any) -> None:
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


def test_flags_are_fixed_when_the_plan_is_built() -> None:
    @get("/", return_dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])
    async def read() -> Response[Optional[DCPerson]]:
        return Response(None)

    app = Litestar([read], openapi_config=None)
    backend = not_none(not_none(app.route_handler_method_map["/"]["GET"]._dto_plan).return_).backend

    assert (backend._passes_none, backend._wrapped_passes_none) == (False, True)


def test_builtins_decoder_returns_none_for_optional_annotation() -> None:
    @post("/", dto=DataclassDTO[Annotated[DCPerson, EXCLUDE]])
    async def create(data: URLEncodedBody[Optional[DCPerson]] = None) -> None:
        return None

    app = Litestar([create], openapi_config=None)
    backend = not_none(not_none(app.route_handler_method_map["/"]["POST"]._dto_plan).data).backend

    assert backend.populate_data_from_builtins(None, RequestFactory().get()) is None
