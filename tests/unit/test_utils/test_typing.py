# ruff: noqa: UP007, UP006

from __future__ import annotations

from sys import version_info
from typing import Any, Dict, List, Optional, Union

import pytest
from typing_extensions import Annotated

from litestar.utils.typing import get_origin_or_inner_type, make_non_optional_union
from tests.models import DataclassPerson, DataclassPet  # noqa: F401

if version_info >= (3, 10):
    from collections import deque  # noqa: F401

    py_310_plus_annotation = [
        (eval(tp), exp)
        for tp, exp in [
            ("tuple[DataclassPerson, ...]", True),
            ("list[DataclassPerson]", True),
            ("deque[DataclassPerson]", True),
            ("tuple[DataclassPet, ...]", False),
            ("list[DataclassPet]", False),
            ("deque[DataclassPet]", False),
        ]
    ]
else:
    py_310_plus_annotation = []


@pytest.mark.parametrize(
    ("annotation", "expected"), [(Union[None, str, int], Union[str, int]), (Optional[Union[str, int]], Union[str, int])]
)
def test_make_non_optional_union(annotation: Any, expected: Any) -> None:
    assert make_non_optional_union(annotation) == expected


def test_get_origin_or_inner_type() -> None:
    assert get_origin_or_inner_type(List[DataclassPerson]) == list
    assert get_origin_or_inner_type(Annotated[List[DataclassPerson], "foo"]) == list
    assert get_origin_or_inner_type(Annotated[Dict[str, List[DataclassPerson]], "foo"]) == dict
