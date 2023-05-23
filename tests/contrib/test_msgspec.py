from __future__ import annotations

from typing import TYPE_CHECKING

from msgspec import Meta, Struct, field
from typing_extensions import Annotated

from litestar.contrib.msgspec import MsgspecDTO
from litestar.dto.factory import dto_field
from litestar.dto.factory.types import FieldDefinition
from litestar.typing import ParsedType

if TYPE_CHECKING:
    from typing import Callable


def test_field_definition_generation(
    int_factory: Callable[[], int], expected_field_defs: list[FieldDefinition]
) -> None:
    class TestStruct(Struct):
        a: int
        b: Annotated[int, Meta(extra=dto_field("read-only"))]
        c: Annotated[int, Meta(gt=1)]
        d: int = field(default=1)
        e: int = field(default_factory=int_factory)

    field_defs = list(MsgspecDTO.generate_field_definitions(TestStruct))
    assert (
        field_defs[0].unique_model_name
        == "tests.contrib.test_msgspec.test_field_definition_generation.<locals>.TestStruct"
    )
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_detect_nested_field() -> None:
    class TestStruct(Struct):
        a: int

    class NotStruct:
        pass

    assert MsgspecDTO.detect_nested_field(ParsedType(TestStruct)) is True
    assert MsgspecDTO.detect_nested_field(ParsedType(NotStruct)) is False
