# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar

import msgspec
import pytest

from litestar import Litestar, Response, get, post, websocket_listener
from litestar.datastructures import UploadFile
from litestar.dto import DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.handlers import websocket_stream
from litestar.params import JSONBody, MultipartBody, URLEncodedBody
from litestar.testing import TestClient, create_test_client

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


@dataclass
class Upload:
    title: str
    file: UploadFile


EXCLUDE = DTOConfig(exclude={"secret"})
PersonDTO = DataclassDTO[Annotated[DCPerson, EXCLUDE]]
LIBRARIES = [(DCPerson, PersonDTO), (MSPerson, MsgspecDTO[Annotated[MSPerson, EXCLUDE]])]
MARKERS: dict[str, Any] = {"json": JSONBody, "urlencoded": URLEncodedBody, "multipart": MultipartBody}
PAYLOAD = {"id": "1", "name": "a", "secret": "x"}


def _send(client: TestClient[Any], encoding: str, payload: Any) -> Any:
    if payload is None or payload == b"null":
        content_type = {"json": "application/json", "urlencoded": "application/x-www-form-urlencoded"}
        headers = {"content-type": content_type.get(encoding, "multipart/form-data; boundary=x")}
        return client.post("/", headers=headers, content=payload or (b"--x--\r\n" if encoding == "multipart" else b""))
    if encoding == "json":
        return client.post("/", json={key: int(value) if key == "id" else value for key, value in payload.items()})
    if encoding == "urlencoded":
        return client.post("/", data=payload)
    return client.post("/", files={key: (None, value) for key, value in payload.items()})


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        pytest.param(lambda m: Optional[m], lambda m: None, id="optional"),
        pytest.param(lambda m: Optional[list[m]], lambda m: None, id="optional-collection"),  # type: ignore[valid-type]
        pytest.param(lambda m: Response[Optional[m]], lambda m: Response(None), id="response-optional"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Wrapper[m]], lambda m: None, id="optional-wrapper"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Response[Optional[m]]], lambda m: None, id="optional-response"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[Response[Optional[m]]], lambda m: Response(None), id="response-none"),  # type: ignore[valid-type]
        pytest.param(lambda m: Optional[m], lambda m: m(id=1, name="a", secret="x"), id="optional-value"),
    ],
)
def test_none_passes_through_returned_optional(
    model: Any, dto: Any, annotation: Callable[[Any], Any], value: Callable[[Any], Any]
) -> None:
    def handler(path: str, **options: Any) -> Any:
        async def read() -> Any:
            return value(model)

        read.__annotations__ = {"return": annotation(model)}
        return get(path, **options)(read)

    with create_test_client([handler("/dto", return_dto=dto), handler("/plain", return_dto=None)]) as client:
        with_dto = client.get("/dto")
        plain = client.get("/plain")

    assert with_dto.status_code == plain.status_code == 200
    assert with_dto.headers.get("content-type") == plain.headers.get("content-type")
    if value(model) is None or isinstance(value(model), Response):
        assert with_dto.content == plain.content
    else:
        assert with_dto.json() == {"id": 1, "name": "a"}


@pytest.mark.parametrize("dto_data", [False, True])
@pytest.mark.parametrize(
    ("encoding", "payload", "expected"),
    [
        pytest.param("json", b"null", None, id="json-null"),
        pytest.param("json", None, None, id="json-empty"),
        pytest.param("multipart", None, None, id="multipart-empty"),
        *(pytest.param(encoding, PAYLOAD, DCPerson(id=1, name="a"), id=f"{encoding}-value") for encoding in MARKERS),
    ],
)
def test_none_passes_through_received_optional(encoding: str, payload: Any, expected: Any, dto_data: bool) -> None:
    received: list[Any] = []

    async def create(data: Any = None) -> None:
        received.append(data.create_instance() if dto_data and data is not None else data)

    inner = DTOData[DCPerson] if dto_data else DCPerson
    create.__annotations__ = {"data": MARKERS[encoding][Optional[inner]], "return": None}

    with create_test_client([post("/", dto=PersonDTO)(create)]) as client:
        assert _send(client, encoding, payload).status_code == 201
    assert received == [expected]


@pytest.mark.parametrize(("model", "dto"), LIBRARIES)
def test_none_passes_through_websocket_optional(model: Any, dto: Any) -> None:
    async def listener(data: str) -> Any:
        return None if data == "none" else model(id=1, name=data, secret="x")

    async def stream() -> AsyncGenerator[Any, None]:
        yield None
        yield model(id=1, name="a", secret="x")

    listener.__annotations__ = {"data": str, "return": Optional[model]}
    stream.__annotations__ = {"return": AsyncGenerator[Optional[model], None]}
    handlers = [
        websocket_listener("/listener", return_dto=dto)(listener),
        websocket_stream("/stream", return_dto=dto)(stream),
    ]

    with create_test_client(handlers) as client:
        with client.websocket_connect("/listener") as ws:
            ws.send_text("none")
            ws.send_text("a")
            assert ws.receive_json() == {"id": 1, "name": "a"}
        with client.websocket_connect("/stream") as ws:
            assert ws.receive_text() == "null"
            assert ws.receive_json() == {"id": 1, "name": "a"}


@pytest.mark.parametrize("encoding", ["urlencoded", "multipart"])
@pytest.mark.parametrize(
    ("dto_data", "payload", "detail"),
    [
        pytest.param(False, {"name": "a"}, "Object missing required field `id`", id="missing"),
        pytest.param(False, {"id": "abc", "name": "a"}, "Expected `int`, got `str` - at `$.id`", id="wrong-type"),
        pytest.param(False, None, "Object missing required field `id`", id="empty"),
        pytest.param(True, {"name": "a"}, "Object missing required field `id`", id="dto-data-missing"),
    ],
)
def test_invalid_form_data_is_400(encoding: str, dto_data: bool, payload: Any, detail: str) -> None:
    received: list[Any] = []

    async def create(data: Any) -> None:
        received.append(data)

    create.__annotations__ = {"data": MARKERS[encoding][DTOData[DCPerson] if dto_data else DCPerson], "return": None}

    with create_test_client([post("/", dto=PersonDTO, return_dto=None)(create)]) as client:
        response = _send(client, encoding, payload)

    assert response.status_code == 400
    assert response.json() == {"status_code": 400, "detail": detail}
    assert received == []


@pytest.mark.parametrize(
    ("annotation", "dto", "files", "expected"),
    [
        pytest.param(Upload, DataclassDTO[Upload], [("title", (None, "t")), ("file", ("a.txt", b"a"))], ["a.txt"]),
        pytest.param(list[UploadFile], None, [("f", ("a.txt", b"a")), ("f", ("b.txt", b"b"))], ["a.txt", "b.txt"]),
        pytest.param(UploadFile, None, [("data", ("a.txt", b"a"))], ["a.txt"]),
    ],
)
def test_multipart_upload_files(annotation: Any, dto: Any, files: Any, expected: list[str]) -> None:
    async def create(data: Any) -> list[str]:
        uploads = data if isinstance(data, list) else [data.file if isinstance(data, Upload) else data]
        return [upload.filename for upload in uploads]

    create.__annotations__ = {"data": MARKERS["multipart"][annotation], "return": list[str]}
    app = Litestar([post("/", **({"dto": dto} if dto else {}))(create)], dto=PersonDTO, openapi_config=None)

    with TestClient(app) as client:
        response = client.post("/", files=files)

    assert response.status_code == 201
    assert response.json() == expected


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
        pytest.param(dict[str, Optional[DCPerson]], {"k": None}, {"k": None}, {"k": None}, id="dict-of-optional"),
        pytest.param(OptionalWrapper[DCPerson], OptionalWrapper(), None, {"data": None}, id="optional-wrapper-none"),
        pytest.param(OptionalWrapper[DCPerson], OptionalWrapper(PERSON), None, {"data": ENCODED}, id="wrapper-value"),
    ],
)
def test_optional_and_nested_collections_round_trip(annotation: Any, value: Any, sent: Any, expected: Any) -> None:
    received: list[Any] = []

    async def read() -> Any:
        return value

    async def create(data: Any) -> None:
        received.append(data)

    read.__annotations__ = {"return": annotation}
    create.__annotations__ = {"data": MARKERS["json"][annotation], "return": None}
    route_handlers = [get("/", return_dto=PersonDTO)(read)]
    if sent is not None:
        route_handlers.append(post("/", dto=PersonDTO)(create))

    with create_test_client(route_handlers) as client:
        response = client.get("/")
        created_status = client.post("/", json=sent).status_code if sent is not None else 201

    assert (response.status_code, response.json(), created_status) == (200, expected, 201)
    assert received == ([value] if sent is not None else [])
