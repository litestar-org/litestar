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


@pytest.fixture
def without_cli_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``click`` and ``rich-click`` not being installed.

    A ``None`` entry in ``sys.modules`` makes the corresponding import raise
    ``ImportError``. The already-imported ``litestar.cli`` submodules are evicted so the
    entrypoint re-imports them and hits that error.
    """
    monkeypatch.setitem(sys.modules, "click", None)
    monkeypatch.setitem(sys.modules, "rich_click", None)
    for name in list(sys.modules):
        if name.startswith("litestar.cli"):
            monkeypatch.delitem(sys.modules, name)


@pytest.mark.usefixtures("without_cli_extra")
def test_run_cli_without_cli_extra() -> None:
    """Running the console script without the ``cli`` extra must give an actionable error.

    ``click`` and ``rich-click`` are only installed by the ``cli`` extra, so the entrypoint
    has to translate the resulting ``ImportError`` instead of letting it surface raw.
    """
    with pytest.raises(MissingDependencyException, match=r"litestar\[cli\]"):
        run_cli()
