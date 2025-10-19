import os
from functools import partial
from typing import Any, Generic, TypeVar

import pytest

from litestar.utils.helpers import envflag, get_name, unique_name_for_scope, unwrap_partial

T = TypeVar("T")


class GenericFoo(Generic[T]): ...


class Foo: ...


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (Foo, "Foo"),
        (Foo(), "Foo"),
        (GenericFoo, "GenericFoo"),
        (GenericFoo[int], "GenericFoo"),
        (GenericFoo[T], "GenericFoo"),  # type: ignore[valid-type]
        (GenericFoo(), "GenericFoo"),
    ),
)
def test_get_name(value: Any, expected: str) -> None:
    assert get_name(value) == expected


def test_unwrap_partial() -> None:
    def func(*args: int) -> int:
        return sum(args)

    wrapped = partial(partial(partial(func, 1), 2))

    assert wrapped() == 3
    assert unwrap_partial(wrapped) is func


def test_unique_name_for_scope() -> None:
    assert unique_name_for_scope("a", []) == "a_0"

    assert unique_name_for_scope("a", ["a", "a_0", "b"]) == "a_1"

    assert unique_name_for_scope("b", ["a", "a_0", "b"]) == "b_0"


def test_envflag_truthy_values() -> None:
    for value in ("1", "true", "TRUE", "t", "T", "yes", "YES", "on", "ON", "y", "Y"):
        os.environ["TEST_FLAG"] = value
        assert envflag("TEST_FLAG") is True
        del os.environ["TEST_FLAG"]


def test_envflag_falsy_values() -> None:
    for value in ("0", "false", "no", "off", ""):
        os.environ["TEST_FLAG"] = value
        assert envflag("TEST_FLAG") is False
        del os.environ["TEST_FLAG"]


def test_envflag_missing() -> None:
    assert envflag("NONEXISTENT_VAR") is False
    assert envflag("NONEXISTENT_VAR_123", default=True) is True
    assert envflag("NONEXISTENT_VAR_456", default=False) is False


def test_envflag_overrides_default() -> None:
    os.environ["TEST_FLAG"] = "true"
    assert envflag("TEST_FLAG", default=False) is True
    del os.environ["TEST_FLAG"]

    os.environ["TEST_FLAG"] = "0"
    assert envflag("TEST_FLAG", default=True) is False
    del os.environ["TEST_FLAG"]


def test_envflag_empty_string_uses_default() -> None:
    os.environ["TEST_FLAG"] = ""
    assert envflag("TEST_FLAG", default=True) is True
    assert envflag("TEST_FLAG", default=False) is False
    del os.environ["TEST_FLAG"]
