from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from pytest import MonkeyPatch, fixture
from pytest_mock import MockerFixture

import starlite.cli
from examples.hello_world import app as hello_world_app
from starlite import Starlite
from starlite.cli import (
    StarliteCLIException,
    StarliteEnv,
    _autodiscover_app,
    _format_is_enabled,
)
from starlite.cli import cli as cli_command
from starlite.utils.cli import on_cli_init


@contextmanager
def create_app_file(path: str | Path) -> Generator[Path, None, None]:
    tmp_path = Path.cwd() / path
    tmp_path.write_text(
        """
from starlite import Starlite
app = Starlite([])
"""
    )
    try:
        yield tmp_path
    finally:
        tmp_path.unlink()


@fixture
def runner() -> CliRunner:
    return CliRunner()


@fixture
def mock_uvicorn_run(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("uvicorn.run")


@fixture
def app_file() -> Generator[Path, None, None]:
    with create_app_file("asgi.py") as path:
        yield path


@fixture
def mock_confirm_ask(mocker: MockerFixture) -> Generator[MagicMock, None, None]:
    yield mocker.patch("starlite.cli.Confirm.ask", return_value=True)


def test_format_is_enabled() -> None:
    assert _format_is_enabled(0) == "[red]Disabled[/]"
    assert _format_is_enabled(False) == "[red]Disabled[/]"
    assert _format_is_enabled("") == "[red]Disabled[/]"
    assert _format_is_enabled(1) == "[green]Enabled[/]"
    assert _format_is_enabled(True) == "[green]Enabled[/]"
    assert _format_is_enabled("a") == "[green]Enabled[/]"


@pytest.mark.parametrize("path_env", ["foo.bar:baz", None])
@pytest.mark.parametrize(
    "debug_env,debug_expected",
    [("true", True), ("True", True), ("1", True), ("0", False), (None, False)],
)
def test_starlite_env_from_env(
    monkeypatch: MonkeyPatch,
    debug_env: str | None,
    debug_expected: bool,
    path_env: str | None,
) -> None:
    if path_env is not None:
        monkeypatch.setenv("STARLITE_APP", "foo.bar:baz")
    if debug_env is not None:
        monkeypatch.setenv("STARLITE_DEBUG", debug_env)

    env = StarliteEnv.from_env()
    assert env.debug is debug_expected
    assert env.app_path == path_env


def test_autodiscover_from_env() -> None:
    env = StarliteEnv(app_path="examples.hello_world:app", debug=False)
    path, app = _autodiscover_app(env)
    assert path == "examples.hello_world:app"
    assert app is hello_world_app


@pytest.mark.parametrize("path", ["asgi.py", "app.py", "application.py"])
def test_autodiscover_from_files(path: str) -> None:
    with create_app_file(path) as tmp_file_path:
        app_path, app = _autodiscover_app(StarliteEnv.from_env())
    assert isinstance(app, Starlite)
    assert app_path == f"{tmp_file_path.stem}:app"


def test_autodiscover_not_found() -> None:
    with pytest.raises(StarliteCLIException):
        _autodiscover_app(StarliteEnv(app_path=None, debug=False))


def test_info_command(mocker: MockerFixture, runner: CliRunner, app_file: Path) -> None:
    mock = mocker.patch("starlite.cli._show_app_info")
    result = runner.invoke(cli_command, ["info"])

    assert result.exception is None
    mock.assert_called_once()


@pytest.mark.parametrize("custom_app_file", [Path("my_app.py"), None])
@pytest.mark.parametrize("host", ["0.0.0.0", None])
@pytest.mark.parametrize("port", [8081, None])
@pytest.mark.parametrize("reload", [True, False, None])
def test_run_command(
    mocker: MockerFixture,
    runner: CliRunner,
    mock_uvicorn_run: MagicMock,
    reload: bool | None,
    port: int | None,
    host: str | None,
    custom_app_file: Path | None,
) -> None:
    mock_show_app_info = mocker.patch("starlite.cli._show_app_info")

    args = ["run"]
    if reload:
        args.append("--reload")
    else:
        reload = False

    if port:
        args.extend(["--port", str(port)])
    else:
        port = 8000

    if host:
        args.extend(["--host", host])
    else:
        host = "127.0.0.1"

    if custom_app_file:
        args.extend(["--app", f"{custom_app_file.stem}:app"])

    with create_app_file(custom_app_file or "asgi.py") as path:

        result = runner.invoke(cli_command, args)

    assert result.exception is None
    assert result.exit_code == 0

    mock_uvicorn_run.assert_called_once_with(f"{path.stem}:app", reload=reload, port=port, host=host)
    mock_show_app_info.assert_called_once()


def test_run_command_force_debug(app_file: Path, mocker: MockerFixture, runner: CliRunner) -> None:
    mock_app = MagicMock()
    mocker.patch("starlite.cli._autodiscover_app", return_value=(str(app_file), mock_app))

    runner.invoke(cli_command, "run --debug")

    assert mock_app.debug is True


def test_delete_session_no_backend(runner: CliRunner, app_file: Path) -> None:
    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_delete_session_cookie_backend(runner: CliRunner, app_file: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("STARLITE_APP", "examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_delete_session(
    runner: CliRunner, monkeypatch: MonkeyPatch, mocker: MockerFixture, mock_confirm_ask: MagicMock
) -> None:
    monkeypatch.setenv("STARLITE_APP", "examples.middleware.session.memory_backend:app")
    mock_delete = mocker.patch("starlite.middleware.session.memory_backend.MemoryBackend.delete")

    result = runner.invoke(cli_command, ["sessions", "delete", "foo"])

    assert mock_confirm_ask.called_once_with("[red]Delete session 'foo'?")
    assert not result.exception
    mock_delete.assert_called_once_with("foo")


def test_clear_sessions_no_backend(runner: CliRunner, app_file: Path) -> None:
    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_clear_sessions_cookie_backend(runner: CliRunner, app_file: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("STARLITE_APP", "examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_clear_sessions(
    runner: CliRunner, monkeypatch: MonkeyPatch, mocker: MockerFixture, mock_confirm_ask: MagicMock
) -> None:
    monkeypatch.setenv("STARLITE_APP", "examples.middleware.session.memory_backend:app")
    mock_delete = mocker.patch("starlite.middleware.session.memory_backend.MemoryBackend.delete_all")

    result = runner.invoke(cli_command, ["sessions", "clear"])

    assert mock_confirm_ask.called_once_with("[red]Delete all sessions?")
    assert not result.exception
    mock_delete.assert_called_once()


def test_cli_init_callback(runner: CliRunner, app_file: Path) -> None:
    mock = MagicMock()

    on_cli_init(mock)
    runner.invoke(cli_command, "info")

    mock.assert_called_once_with(cli_command)
