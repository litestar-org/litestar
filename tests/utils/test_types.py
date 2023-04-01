from collections import deque
from sys import version_info
from typing import Any, Deque, Iterable, List, Optional, Sequence, Tuple, Union

import pytest

from starlite.utils.typing import annotation_is_iterable_of_type, make_non_optional_union
from tests import Person, Pet

if version_info >= (3, 10):
    py_310_plus_annotation = [
        (tuple[Person, ...], True),
        (list[Person], True),
        (deque[Person], True),
        (tuple[Pet, ...], False),
        (list[Pet], False),
        (deque[Pet], False),
    ]
else:
    py_310_plus_annotation = []


@pytest.mark.parametrize(
    "annotation, expected",
    (
        (List[Person], True),
        (Sequence[Person], True),
        (Iterable[Person], True),
        (Tuple[Person, ...], True),
        (Deque[Person], True),
        (List[Pet], False),
        (Sequence[Pet], False),
        (Iterable[Pet], False),
        (Tuple[Pet, ...], False),
        (Deque[Pet], False),
        *py_310_plus_annotation,
        (int, False),
        (str, False),
        (bool, False),
    ),
)
def test_annotation_is_iterable_of_type(annotation: Any, expected: bool) -> None:
    assert annotation_is_iterable_of_type(annotation=annotation, type_value=Person) is expected


@pytest.mark.parametrize(
    ("annotation", "expected"), [(Union[None, str, int], Union[str, int]), (Optional[Union[str, int]], Union[str, int])]
)
def test_make_non_optional_union(annotation: Any, expected: Any) -> None:
    assert make_non_optional_union(annotation) == expected
