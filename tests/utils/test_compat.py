from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from starlite.utils.compat import py_39_safe_annotations

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.parametrize("version", (10, 11))
def test_py39_safe_annotations_on_higher_versions(version: int, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, version))

    def func(a: int | str) -> None:
        ...

    with py_39_safe_annotations(func):
        assert func.__annotations__["a"] == "int | str"


@pytest.mark.parametrize("version", (8, 9))
def test_py39_safe_annotations_on_39(version: int, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, version))

    def func(a: int | str) -> None:
        ...

    assert func.__annotations__["a"] == "int | str"
    with py_39_safe_annotations(func):
        assert func.__annotations__["a"] == "Union[int,str]"
    assert func.__annotations__["a"] == "int | str"
