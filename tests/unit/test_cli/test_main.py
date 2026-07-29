"""Tests for the ``litestar`` console script entrypoint."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from litestar.__main__ import run_cli
from litestar.exceptions import MissingDependencyException

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_cli_invokes_litestar_group(mocker: MockerFixture) -> None:
    litestar_group = mocker.patch("litestar.cli.main.litestar_group")

    run_cli()

    litestar_group.assert_called_once_with()


def test_run_cli_without_cli_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the console script without the ``cli`` extra must give an actionable error.

    ``click`` and ``rich-click`` are only installed by the ``cli`` extra, so the entrypoint
    has to translate the resulting ``ImportError`` instead of letting it surface raw.
    """
    # Simulate click and rich-click not being installed: a None entry makes the import
    # raise ImportError.
    monkeypatch.setitem(sys.modules, "click", None)
    monkeypatch.setitem(sys.modules, "rich_click", None)
    for name in list(sys.modules):
        if name.startswith("litestar.cli"):
            monkeypatch.delitem(sys.modules, name)

    with pytest.raises(MissingDependencyException, match=r"litestar\[cli\]"):
        run_cli()
