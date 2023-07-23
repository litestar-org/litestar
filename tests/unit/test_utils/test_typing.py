from __future__ import annotations

from collections import deque
from sys import version_info
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pytest
from typing_extensions import Annotated

from litestar.utils.typing import annotation_is_iterable_of_type, get_origin_or_inner_type, make_non_optional_union
from tests import PydanticPerson, PydanticPet

if version_info >= (3, 10):
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
