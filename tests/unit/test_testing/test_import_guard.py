"""Tests for the ``litestar.testing`` optional dependency guard."""

from __future__ import annotations

import importlib
import sys

import pytest

from litestar.exceptions import MissingDependencyException


def test_testing_requires_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """``litestar.testing`` must point at the ``testing`` extra when httpx is missing.

    ``httpx`` is only installed by the ``testing`` extra, so importing the public test
    client helpers without it has to raise an actionable error rather than a bare
    ``ModuleNotFoundError``.
    """
    # Simulate httpx not being installed: a None entry makes `import httpx` raise ImportError.
    monkeypatch.setitem(sys.modules, "httpx", None)
    monkeypatch.delitem(sys.modules, "litestar.testing", raising=False)

    with pytest.raises(MissingDependencyException, match=r"litestar\[testing\]"):
        importlib.import_module("litestar.testing")
