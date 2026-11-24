from dataclasses import dataclass
from typing import Annotated, Any, Optional, cast

import pytest

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.dto import DataclassDTO, DTOConfig, DTOData
from litestar.enums import RequestEncodingType
from litestar.params import Body, JSONBody, MultipartBody, URLEncodedBody
from litestar.testing import TestClient, create_test_client


@dataclass
class User:
    id: int
    name: str
    secret: str = "s"


@dataclass
class Upload:
    title: str
    file: UploadFile


UserDTO = DataclassDTO[Annotated[User, DTOConfig(exclude={"secret"})]]
MISSING_ID = {"status_code": 400, "detail": "Object missing required field `id`"}


def _form_client(encoding: str, received: list[Any]) -> TestClient[Any]:
    async def create(data: Any) -> None:
        received.append(data)

    marker = {"json": JSONBody, "urlencoded": URLEncodedBody, "multipart": MultipartBody}[encoding]
    create.__annotations__ = {"data": cast("Any", marker)[User], "return": None}
    return create_test_client([post("/", dto=UserDTO, return_dto=None)(create)])


def _send(client: TestClient[Any], encoding: str, payload: dict[str, str] | None) -> Any:
    if encoding == "json":
        return client.post("/", json=payload or {})
    if payload is None:
        return client.post("/", headers={"content-type": "application/x-www-form-urlencoded"})
    if encoding == "urlencoded":
        return client.post("/", data=payload)
    return client.post("/", files={key: (None, value) for key, value in payload.items()})


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        pytest.param({"name": "a"}, "Object missing required field `id`", id="missing"),
        pytest.param({"id": "abc", "name": "a"}, "Expected `int`, got `str` - at `$.id`", id="wrong-type"),
        pytest.param(None, "Object missing required field `id`", id="empty"),
    ],
)
@pytest.mark.parametrize("encoding", ["json", "urlencoded", "multipart"])
def test_form_body_invalid_input_is_400(encoding: str, payload: dict[str, str] | None, detail: str) -> None:
    received: list[Any] = []

    with _form_client(encoding, received) as client:
        response = _send(client, encoding, payload)

    assert response.status_code == 400
    assert response.json() == {"status_code": 400, "detail": detail}
    assert received == []


def test_multipart_dto_data_invalid_input_is_400() -> None:
    @post("/", dto=UserDTO, return_dto=None)
    async def create(data: MultipartBody[DTOData[User]]) -> None: ...

    with create_test_client([create]) as client:
        response = client.post("/", files={"name": (None, "a")})

    assert response.status_code == 400
    assert response.json() == MISSING_ID


def test_multipart_model_with_upload_file_field() -> None:
    received: list[Any] = []

    @post("/", dto=DataclassDTO[Upload], return_dto=None)
    async def create(data: MultipartBody[Upload]) -> None:
        received.append(data)

    with create_test_client([create]) as client:
        valid = client.post("/", files={"title": (None, "t"), "file": ("a.txt", b"content")})
        missing = client.post("/", files={"file": ("a.txt", b"content")})

    assert valid.status_code == 201
    assert received[0].title == "t"
    assert isinstance(received[0].file, UploadFile)
    assert missing.status_code == 400
    assert missing.json() == {"status_code": 400, "detail": "Object missing required field `title`"}


def test_multipart_optional_body_empty_form_is_none() -> None:
    received: list[Any] = []

    @post("/", dto=UserDTO, return_dto=None)
    async def create(data: MultipartBody[Optional[User]] = None) -> None:
        received.append(data)

    with create_test_client([create]) as client:
        response = client.post("/", headers={"content-type": "multipart/form-data; boundary=x"}, content=b"--x--\r\n")

    assert response.status_code == 201
    assert received == [None]


@pytest.mark.parametrize(
    ("annotation", "files", "expected"),
    [
        pytest.param(list[UploadFile], [("f", ("a.txt", b"a")), ("f", ("b.txt", b"b"))], ["a.txt", "b.txt"], id="list"),
        pytest.param(UploadFile, [("data", ("a.txt", b"a"))], ["a.txt"], id="single"),
    ],
)
def test_layer_dto_does_not_touch_upload_file_bodies(annotation: Any, files: Any, expected: list[str]) -> None:
    async def create(data: Any) -> list[str]:
        uploads = data if isinstance(data, list) else [data]
        return [upload.filename for upload in uploads]

    create.__annotations__ = {
        "data": Annotated[annotation, Body(media_type=RequestEncodingType.MULTI_PART)],
        "return": list[str],
    }
    app = Litestar([post("/")(create)], dto=UserDTO, openapi_config=None)

    with TestClient(app) as client:
        response = client.post("/", files=files)

    assert response.status_code == 201
    assert response.json() == expected
