# ruff: noqa: UP007
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pytest
from typing_extensions import Annotated

from litestar import patch, post
from litestar.datastructures import UploadFile
from litestar.dto.factory import DTOConfig, DTOData, dto_field
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.dto.factory.types import RenameStrategy
from litestar.enums import MediaType, RequestEncodingType
from litestar.params import Body
from litestar.response.base import Response
from litestar.testing import create_test_client


def test_url_encoded_form_data() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: User = Body(media_type=RequestEncodingType.URL_ENCODED)) -> User:
        return data

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


async def test_multipart_encoded_form_data() -> None:
    @dataclass
    class Payload:
        file: UploadFile
        forbidden: UploadFile = field(
            default=UploadFile(content_type="text/plain", filename="forbidden", file_data=b"forbidden"),
            metadata=dto_field("read-only"),
        )

    @post(
        dto=DataclassDTO[Payload], return_dto=None, signature_namespace={"Payload": Payload}, media_type=MediaType.TEXT
    )
    async def handler(data: Payload = Body(media_type=RequestEncodingType.MULTI_PART)) -> bytes:
        return await data.forbidden.read()

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post(
            "/",
            files={"file": b"abc123", "forbidden": b"123abc"},
        )
        assert response.content == b"forbidden"


def test_renamed_field() -> None:
    @dataclass
    class Foo:
        bar: str

    config = DTOConfig(rename_fields={"bar": "baz"})
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Foo:
        assert data.bar == "hello"
        return data

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post("/", json={"baz": "hello"})
        assert response.json() == {"baz": "hello"}


@dataclass
class Spam:
    main_id: str = "spam-id"


@dataclass
class Foo:
    bar: str = "hello"
    SPAM: str = "bye"
    spam_bar: str = "welcome"
    spam_model: Optional[Spam] = None


@pytest.mark.parametrize(
    "rename_strategy, instance, tested_fields, data",
    [
        ("upper", Foo(bar="hi"), ["BAR"], {"BAR": "hi"}),
        ("lower", Foo(SPAM="goodbye"), ["spam"], {"spam": "goodbye"}),
        (lambda x: x[::-1], Foo(bar="h", SPAM="bye!"), ["rab", "MAPS"], {"rab": "h", "MAPS": "bye!"}),
        ("camel", Foo(spam_bar="star"), ["spamBar"], {"spamBar": "star"}),
        ("pascal", Foo(spam_bar="star"), ["SpamBar"], {"SpamBar": "star"}),
        ("camel", Foo(spam_model=Spam()), ["spamModel"], {"spamModel": {"mainId": "spam-id"}}),
    ],
)
def test_fields_alias_generator(
    rename_strategy: RenameStrategy,
    instance: Foo,
    tested_fields: list[str],
    data: dict[str, str],
) -> None:
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Foo:
        assert data.bar == instance.bar
        assert data.SPAM == instance.SPAM
        return data

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response_callback = client.post("/", json=data)
        assert all(response_callback.json()[f] == data[f] for f in tested_fields)


def test_dto_data_injection() -> None:
    @dataclass
    class Foo:
        bar: str

    @post(dto=DataclassDTO[Foo], return_dto=None, signature_namespace={"Foo": Foo})
    def handler(data: DTOData[Foo]) -> Foo:
        assert isinstance(data, DTOData)
        assert data.as_builtins() == {"bar": "hello"}
        assert isinstance(data.create_instance(), Foo)
        return data.create_instance()

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post("/", json={"bar": "hello"})
        assert response.json() == {"bar": "hello"}


def test_dto_data_with_url_encoded_form_data() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: DTOData[User] = Body(media_type=RequestEncodingType.URL_ENCODED)) -> User:
        return data.create_instance()

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


def test_dto_data_with_patch_request() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    class PatchDTO(DataclassDTO[User]):
        config = DTOConfig(partial=True)

    @patch(dto=PatchDTO, return_dto=None, signature_namespace={"User": User})
    def handler(data: DTOData[User]) -> User:
        return data.update_instance(User(name="John", age=42))

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.patch("/", json={"age": 41, "read_only": "whoops"})
        assert response.json() == {"name": "John", "age": 41, "read_only": "read-only"}


def test_dto_openapi_model_name_collision() -> None:
    @dataclass
    class Bar:
        id: int
        foo: str

    write_dto = DataclassDTO[Annotated[Bar, DTOConfig(exclude={"id"})]]
    read_dto = DataclassDTO[Bar]

    @post(dto=write_dto, return_dto=read_dto, signature_namespace={"Bar": Bar})
    def handler(data: Bar) -> Bar:
        return data

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 2
        assert schemas[0] != schemas[1]
        assert all(
            k.startswith("tests.dto.factory.test_integration.test_dto_openapi_model_name_collision.<locals>.Bar")
            for k in response.json()["components"]["schemas"]
        )


def test_dto_with_explicit_Response_return() -> None:
    @dataclass
    class Foo:
        bar: str

    config = DTOConfig(rename_strategy="upper")
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, return_dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Response[Foo]:
        # return data
        return Response(data)

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post("/", json={"BAR": "hello"})
        assert response.json() == {"BAR": "hello"}

    assert 0
