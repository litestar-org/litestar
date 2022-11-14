from inspect import Signature
from typing import Any, Dict, cast

import pytest

from starlite import Response, get
from starlite.utils import is_class_and_subclass


class C:
    pass


@get("/")
def naive_handler() -> Dict[str, int]:
    return {}


@get("/")
def response_handler() -> Response[Any]:
    return Response(content=b"")


class Sub(C):
    ...


@pytest.mark.parametrize(
    "args, expected",
    (
        ((Sub, C), True),
        ((Signature.from_callable(cast("Any", naive_handler.fn.value)).return_annotation, C), False),
        ((Signature.from_callable(cast("Any", response_handler.fn.value)).return_annotation, Response), True),
        ((Dict[str, Any], C), False),
        ((C(), C), False),
    ),
)
def test_is_class_and_subclass(args: tuple, expected: bool) -> None:
    assert is_class_and_subclass(*args) is expected
