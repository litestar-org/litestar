from functools import partial
from typing import Any, Generic, TypeVar

import pytest

from litestar.exceptions import LitestarException
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


def test_envflag_truthy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("1", "true", "t", "yes", "y", "on", "YeS", "oN", "TRUE", "T"):
        monkeypatch.setenv("TEST_FLAG", value)
        assert envflag("TEST_FLAG") is True
        monkeypatch.delenv("TEST_FLAG")


def test_envflag_falsy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("0", "false", "f", "no", "n", "off", "", "OfF", "fAlSe", "NO"):
        monkeypatch.setenv("TEST_FLAG", value)
        assert envflag("TEST_FLAG") is False
        monkeypatch.delenv("TEST_FLAG")


def test_envflag_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("2", "Tru", "Fals", "maybe", "invalid", "O"):
        monkeypatch.setenv("TEST_FLAG", value)
        with pytest.raises(LitestarException):
            envflag("TEST_FLAG")


def test_envflag_missing() -> None:
    assert envflag("NONEXISTENT_VAR") is None


def test_envflag_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_FLAG", "true")
    assert envflag("TEST_FLAG") is True
    monkeypatch.delenv("TEST_FLAG")

    monkeypatch.setenv("TEST_FLAG", "0")
    assert envflag("TEST_FLAG") is False
    monkeypatch.delenv("TEST_FLAG")


def test_envflag_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_FLAG", "")
    assert envflag("TEST_FLAG") is False
    monkeypatch.delenv("TEST_FLAG")
