from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import ClassVar, List

import pytest

from litestar import post
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.dto.factory.types import FieldDefinition
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import create_test_client
from litestar.types.empty import Empty
from litestar.utils.signature import ParsedType


@dataclass
class Model:
    a: int
    b: str = field(default="b")
    c: List[int] = field(default_factory=list)  # noqa: UP006
    d: ClassVar[float] = 1.0


@pytest.fixture(name="dto_type")
def fx_dto_type() -> type[DataclassDTO[Model]]:
    return DataclassDTO[Model]


@pytest.mark.skipif(sys.version_info > (3, 8), reason="generic builtin collection")
def test_dataclass_field_definitions(dto_type: type[DataclassDTO[Model]]) -> None:
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
        FieldDefinition(name="b", parsed_type=ParsedType(str), default="b"),
        FieldDefinition(name="c", parsed_type=ParsedType(list[int]), default=Empty, default_factory=list),
    ]


@pytest.mark.skipif(sys.version_info < (3, 9), reason="generic builtin collection")
def test_dataclass_field_definitions_38(dto_type: type[DataclassDTO[Model]]) -> None:
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
        FieldDefinition(name="b", parsed_type=ParsedType(str), default="b"),
        FieldDefinition(name="c", parsed_type=ParsedType(List[int]), default=Empty, default_factory=list),
    ]


def test_dataclass_detect_nested(dto_type: type[DataclassDTO[Model]]) -> None:
    assert dto_type.detect_nested_field(FieldDefinition(name="a", parsed_type=ParsedType(Model), default=Empty)) is True
    assert (
        dto_type.detect_nested_field(FieldDefinition(name="a", parsed_type=ParsedType(List[Model]), default=Empty))
        is True
    )
    assert dto_type.detect_nested_field(FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty)) is False


def test_url_encoded_form_data() -> None:
    @dataclass
    class User:
        name: str
        age: int

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: User = Body(media_type=RequestEncodingType.URL_ENCODED)) -> User:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/", content=b"name=John&age=42", headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.json() == {"name": "John", "age": 42}
