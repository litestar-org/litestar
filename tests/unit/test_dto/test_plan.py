from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import pytest

from litestar import Response
from litestar.dto import DataclassDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import DTODirectionPlan, DTOPlan, build_schema_annotation, create_backend
from litestar.exceptions import InvalidAnnotationException
from litestar.params import JSONBody
from litestar.typing import FieldDefinition

T = TypeVar("T")


@dataclass
class Model:
    a: int
    b: str


@dataclass
class OtherModel:
    a: int


@dataclass
class WithCount(Generic[T]):
    count: int
    data: list[T]


def test_create_backend_data_direction() -> None:
    backend = create_backend(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(JSONBody[Model]),
        is_data_field=True,
        handler_id="pkg.handler::1",
    )

    assert backend.is_data_field is True
    assert backend.transfer_model_type.__name__.endswith("RequestBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_return_direction() -> None:
    backend = create_backend(
        DataclassDTO[Model], FieldDefinition.from_annotation(Model), is_data_field=False, handler_id="pkg.handler::1"
    )

    assert backend.is_data_field is False
    assert backend.transfer_model_type.__name__.endswith("ResponseBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_raises_for_mismatched_model() -> None:
    with pytest.raises(InvalidAnnotationException, match="DTO narrowed with"):
        create_backend(
            DataclassDTO[Model], FieldDefinition.from_annotation(OtherModel), is_data_field=False, handler_id="h"
        )


def test_create_backend_raises_for_non_homogeneous_tuple() -> None:
    with pytest.raises(InvalidAnnotationException, match="DTO narrowed with"):
        create_backend(
            DataclassDTO[Model],
            FieldDefinition.from_annotation(tuple[Model, str]),
            is_data_field=False,
            handler_id="h",
        )


def test_create_backend_generic_wrapper() -> None:
    backend = create_backend(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(WithCount[Model]),
        is_data_field=False,
        handler_id="h",
    )

    assert backend.wrapper_attribute_name == "data"
    assert backend.field_definition.annotation == list[Model]


def test_create_backend_uses_backend_cls() -> None:
    class CustomBackend(DTOBackend):
        __slots__ = ()

    backend = create_backend(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(Model),
        is_data_field=False,
        handler_id="h",
        backend_cls=CustomBackend,
    )

    assert type(backend) is CustomBackend


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(Model, lambda backend: backend.transfer_model_type, id="model"),
        pytest.param(list[Model], lambda backend: list[backend.transfer_model_type], id="list"),
        pytest.param(WithCount[Model], lambda backend: WithCount[backend.transfer_model_type], id="generic-wrapper"),
        pytest.param(Response[Model], lambda backend: backend.annotation, id="response"),
    ],
)
def test_build_schema_annotation(annotation: Any, expected: Callable[[DTOBackend], Any]) -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(annotation)
    backend = create_backend(dto, field_definition, is_data_field=False, handler_id="h")

    assert build_schema_annotation(dto, backend, field_definition) == expected(backend)


def test_build_schema_annotation_of_response_ignores_the_wrapper() -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(Response[Model])
    backend = create_backend(dto, field_definition, is_data_field=False, handler_id="h")

    assert backend.wrapper_attribute_name == "content"
    assert build_schema_annotation(dto, backend, field_definition) is backend.annotation


def test_plan_types_are_frozen() -> None:
    dto = DataclassDTO[Model]
    backend = create_backend(dto, FieldDefinition.from_annotation(Model), is_data_field=False, handler_id="h")
    direction = DTODirectionPlan(dto=dto, backend=backend, schema_annotation=backend.annotation)
    plan = DTOPlan(data=None, return_=direction, data_dto=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        direction.backend = backend  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.data_dto = dto  # type: ignore[misc]
