from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from starlite.utils.compat import py_38_safe_annotations

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_py38_safe_annotations_on_39_plus(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 9))

    def func(a: int | str) -> None:
        ...

    with py_38_safe_annotations(func):
        assert func.__annotations__["a"] == "int | str"


def test_py38_safe_annotations_on_38(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 8))

    def func(a: int | str) -> None:
        ...

    assert func.__annotations__["a"] == "int | str"
    with py_38_safe_annotations(func):
        assert func.__annotations__["a"] == "Union[int,str]"
    assert func.__annotations__["a"] == "int | str"
