from typing import Generic, List, Optional, TypeVar

from litestar.dto._utils import resolve_generic_wrapper_type, resolve_model_type
from litestar.typing import FieldDefinition

T = TypeVar("T")


def test_resolve_model_type_optional() -> None:
    field_definition = FieldDefinition.from_annotation(Optional[int])
    assert resolve_model_type(field_definition) == FieldDefinition.from_annotation(int)


def test_resolve_generic_wrapper_type_no_origin() -> None:
    field_definition = FieldDefinition.from_annotation(int)
    assert resolve_generic_wrapper_type(field_definition, int) is None


def test_resolve_generic_wrapper_type_origin_no_parameters() -> None:
    field_definition = FieldDefinition.from_annotation(List[int])
    assert resolve_generic_wrapper_type(field_definition, int) is None


def test_resolve_generic_wrapper_type_model_type_not_subtype_of_specialized_type() -> None:
    class Wrapper(Generic[T]):
        t: T

    field_definition = FieldDefinition.from_annotation(Wrapper[int])

    assert resolve_generic_wrapper_type(field_definition, str) is None


def test_resolve_generic_wrapper_type_type_var_not_attribute() -> None:
    class Wrapper(Generic[T]):
        def returns_t(self) -> T:  # type:ignore[empty-body]
            ...

    field_definition = FieldDefinition.from_annotation(Wrapper[int])

    assert resolve_generic_wrapper_type(field_definition, int) is None
