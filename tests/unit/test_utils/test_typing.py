from __future__ import annotations

from sys import version_info
from typing import Any, Deque, Dict, Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar, Union

import pytest
from typing_extensions import Annotated

from litestar.utils.typing import (
    annotation_is_iterable_of_type,
    get_origin_or_inner_type,
    get_type_hints_with_generics_resolved,
    make_non_optional_union,
)
from tests import PydanticPerson, PydanticPet

if version_info >= (3, 10):
    from collections import deque

    # Pyright will report an error for these types if you are running on python 3.8, we run on >= 3.9 in CI
    # so we can safely ignore that error.
    py_310_plus_annotation = [
        (tuple[PydanticPerson, ...], True),
        (list[PydanticPerson], True),
        (deque[PydanticPerson], True),
        (tuple[PydanticPet, ...], False),
        (list[PydanticPet], False),
        (deque[PydanticPet], False),
    ]
else:
    py_310_plus_annotation = []


@pytest.mark.parametrize(
    "annotation, expected",
    (
        (List[PydanticPerson], True),
        (Sequence[PydanticPerson], True),
        (Iterable[PydanticPerson], True),
        (Tuple[PydanticPerson, ...], True),
        (Deque[PydanticPerson], True),
        (List[PydanticPet], False),
        (Sequence[PydanticPet], False),
        (Iterable[PydanticPet], False),
        (Tuple[PydanticPet, ...], False),
        (Deque[PydanticPet], False),
        *py_310_plus_annotation,
        (int, False),
        (str, False),
        (bool, False),
    ),
)
def test_annotation_is_iterable_of_type(annotation: Any, expected: bool) -> None:
    assert annotation_is_iterable_of_type(annotation=annotation, type_value=PydanticPerson) is expected


@pytest.mark.parametrize(
    ("annotation", "expected"), [(Union[None, str, int], Union[str, int]), (Optional[Union[str, int]], Union[str, int])]
)
def test_make_non_optional_union(annotation: Any, expected: Any) -> None:
    assert make_non_optional_union(annotation) == expected


def test_get_origin_or_inner_type() -> None:
    assert get_origin_or_inner_type(List[PydanticPerson]) == list
    assert get_origin_or_inner_type(Annotated[List[PydanticPerson], "foo"]) == list
    assert get_origin_or_inner_type(Annotated[Dict[str, List[PydanticPerson]], "foo"]) == dict


T = TypeVar("T")
V = TypeVar("V", int, str)
U = TypeVar("U", bound=int)

ANNOTATION = object()


class Foo(Generic[T]):
    foo: T


class BoundFoo(Generic[U]):
    bound_foo: U


class ConstrainedFoo(Generic[V]):
    constrained_foo: V


class AnnotatedFoo(Generic[T]):
    annotated_foo: Annotated[T, ANNOTATION]


class UnionFoo(Generic[T, V, U]):
    union_foo: Union[T, bool]  # noqa: UP007
    constrained_union_foo: Union[V, bool]  # noqa: UP007
    bound_union_foo: Union[U, bool]  # noqa: UP007


@pytest.mark.parametrize(
    ("annotation", "expected_type_hints"),
    (
        (Foo[int], {"foo": int}),
        (BoundFoo, {"bound_foo": int}),
        (BoundFoo[int], {"bound_foo": int}),
        (ConstrainedFoo[int], {"constrained_foo": int}),
        (ConstrainedFoo, {"constrained_foo": Union[int, str]}),
        (AnnotatedFoo[int], {"annotated_foo": Annotated[int, ANNOTATION]}),
        (
            UnionFoo[T, V, U],  # type: ignore[valid-type]
            {
                "union_foo": Union[T, bool],  # pyright: ignore[reportGeneralTypeIssues]
                "constrained_union_foo": Union[int, str, bool],
                "bound_union_foo": Union[int, bool],
            },
        ),
        (
            UnionFoo,
            {
                "union_foo": Union[T, bool],  # pyright: ignore[reportGeneralTypeIssues]
                "constrained_union_foo": Union[int, str, bool],
                "bound_union_foo": Union[int, bool],
            },
        ),
    ),
)
def test_get_type_hints_with_generics(annotation: Any, expected_type_hints: dict[str, Any]) -> None:
    assert get_type_hints_with_generics_resolved(annotation, include_extras=True) == expected_type_hints
