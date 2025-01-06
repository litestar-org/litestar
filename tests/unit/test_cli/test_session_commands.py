from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Litestar
from litestar.cli.commands.sessions import get_session_backend
from litestar.cli.main import litestar_group as cli_command
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from _pytest.monkeypatch import MonkeyPatch
    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def test_get_session_backend() -> None:
    session_middleware = ServerSideSessionConfig().middleware
    app = Litestar([], middleware=[RateLimitConfig(rate_limit=("second", 1)).middleware, session_middleware])

    assert get_session_backend(app) is session_middleware.kwargs["backend"]


def test_delete_session_no_backend(runner: CliRunner, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.hello_world:app")
    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_delete_session_cookie_backend(runner: CliRunner, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_delete_session(
    runner: CliRunner, monkeypatch: MonkeyPatch, mocker: MockerFixture, mock_confirm_ask: MagicMock
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.middleware.session.file_store:app")
    mock_delete = mocker.patch("litestar.stores.file.FileStore.delete")

    result = runner.invoke(cli_command, ["sessions", "delete", "foo"])

    mock_confirm_ask.assert_called_once_with("Delete session 'foo'?")
    assert not result.exception
    mock_delete.assert_called_once_with("foo")


def test_clear_sessions_no_backend(runner: CliRunner, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.hello_world:app")
    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_clear_sessions_cookie_backend(runner: CliRunner, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_clear_sessions(
    runner: CliRunner, monkeypatch: MonkeyPatch, mocker: MockerFixture, mock_confirm_ask: MagicMock
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "docs.examples.middleware.session.file_store:app")
    mock_delete = mocker.patch("litestar.stores.file.FileStore.delete_all")

    result = runner.invoke(cli_command, ["sessions", "clear"])

    mock_confirm_ask.assert_called_once_with("[red]Delete all sessions?")
    assert not result.exception
    mock_delete.assert_called_once()
