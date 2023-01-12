from collections import deque
from sys import version_info
from typing import Any, Deque, Iterable, List, Sequence, Tuple

import pytest

from starlite.utils.types import annotation_is_iterable_of_type
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
