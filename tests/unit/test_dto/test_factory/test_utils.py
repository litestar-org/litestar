from typing import Generic, List, Optional, TypeVar

from litestar.dto.factory.utils import resolve_generic_wrapper_type, resolve_model_type
from litestar.typing import ParsedType

T = TypeVar("T")


def test_resolve_model_type_optional() -> None:
    parsed_type = ParsedType.from_annotation(Optional[int])
    assert resolve_model_type(parsed_type) == ParsedType.from_annotation(int)


def test_resolve_generic_wrapper_type_no_origin() -> None:
    parsed_type = ParsedType.from_annotation(int)
    assert resolve_generic_wrapper_type(parsed_type, int) is None


def test_resolve_generic_wrapper_type_origin_no_parameters() -> None:
    parsed_type = ParsedType.from_annotation(List[int])
    assert resolve_generic_wrapper_type(parsed_type, int) is None


def test_resolve_generic_wrapper_type_model_type_not_subtype_of_specialized_type() -> None:
    class Wrapper(Generic[T]):
        t: T

    parsed_type = ParsedType.from_annotation(Wrapper[int])

    assert resolve_generic_wrapper_type(parsed_type, str) is None


def test_resolve_generic_wrapper_type_type_var_not_attribute() -> None:
    class Wrapper(Generic[T]):
        def returns_t(self) -> T:  # type:ignore[empty-body]
            ...

    parsed_type = ParsedType.from_annotation(Wrapper[int])

    assert resolve_generic_wrapper_type(parsed_type, int) is None
