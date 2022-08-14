from inspect import Signature
from typing import Any, Dict, cast

import pytest

from starlite import get
from starlite.utils import is_class_and_subclass


class C:
    pass


@get("/")
def my_fn() -> Dict[str, int]:
    return {}


class Sub(C):
    ...


@pytest.mark.parametrize(
    "value, expected",
    (
        (is_class_and_subclass(Sub, C), True),
        (is_class_and_subclass(Signature.from_callable(cast("Any", my_fn.fn)).return_annotation, C), False),
        (is_class_and_subclass(Dict[str, Any], C), False),
        (is_class_and_subclass(C(), C), False),
    ),
)
def test_is_class_and_subclass(value: bool, expected: bool) -> None:
    assert value is expected
