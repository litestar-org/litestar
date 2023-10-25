from __future__ import annotations

from typing import TYPE_CHECKING

<<<<<<< HEAD
import pydantic as pydantic_v2
from pydantic import v1 as pydantic_v1
=======
from pydantic import (
    BaseModel,
    ByteSize,
    EmailStr,
    Field,
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
    Json,
    NameEmail,
)
>>>>>>> 9edcb26b (add unit tests for downtyping with PydanticDTO.generate_field_definitions())
from typing_extensions import Annotated

from litestar.contrib.pydantic import PydanticDTO
from litestar.dto import dto_field
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import Callable


def test_field_definition_generation_v1(
    int_factory: Callable[[], int],
    expected_field_defs: list[DTOFieldDefinition],
) -> None:
    class TestModel(pydantic_v1.BaseModel):
        a: int
        b: Annotated[int, pydantic_v1.Field(**dto_field("read-only"))]  # pyright: ignore
        c: Annotated[int, pydantic_v1.Field(gt=1)]
        d: int = pydantic_v1.Field(default=1)
        e: int = pydantic_v1.Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert field_defs[0].model_name == "TestModel"
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_field_definition_generation_v2(
    int_factory: Callable[[], int],
    expected_field_defs: list[DTOFieldDefinition],
) -> None:
    class TestModel(pydantic_v2.BaseModel):
        a: int
        b: Annotated[int, pydantic_v2.Field(**dto_field("read-only"))]  # pyright: ignore
        c: Annotated[int, pydantic_v2.Field(gt=1)]
        d: int = pydantic_v2.Field(default=1)
        e: int = pydantic_v2.Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert field_defs[0].model_name == "TestModel"
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_detect_nested_field(base_model: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]) -> None:
    class TestModel(base_model):  # type: ignore[misc, valid-type]
        a: int

    class NotModel:
        pass

    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(TestModel)) is True
    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(NotModel)) is False


_specialized_generics: list[tuple[type, type]] = [
    (EmailStr, str),
    (ByteSize, int),
    (IPvAnyAddress, str),
    (IPvAnyInterface, str),
    (IPvAnyNetwork, str),
    (Json, str),
    (NameEmail, str),
]


def test_field_definition_generation_with_downtyping() -> None:
    class TestModel(BaseModel):
        a: _specialized_generics[0][0]
        b: _specialized_generics[1][0]
        c: _specialized_generics[2][0]
        d: _specialized_generics[3][0]
        e: _specialized_generics[4][0]
        f: _specialized_generics[5][0]
        g: _specialized_generics[6][0]

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    for i in range(len(field_defs)):
        assert field_defs[i].annotation == _specialized_generics[i][1]