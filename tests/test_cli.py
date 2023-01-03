import importlib
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union
from unittest.mock import MagicMock

import pytest
from click import group
from click.testing import CliRunner
from pytest import MonkeyPatch, fixture
from pytest_mock import MockerFixture

import starlite.cli
from starlite import Starlite
from starlite.cli import (
    AUTODISCOVER_PATHS,
    DiscoveredApp,
    StarliteCLIException,
    StarliteEnv,
    _autodiscover_app,
    _format_is_enabled,
    _get_session_backend,
    _path_to_dotted_path,
)
from starlite.cli import cli as cli_command
from starlite.middleware.rate_limit import RateLimitConfig
from starlite.middleware.session.memory_backend import MemoryBackendConfig

APP_FILE_CONTENT = """
from starlite import Starlite
app = Starlite([])
"""


CREATE_APP_FILE_CONTENT = """
from starlite import Starlite

def create_app():
    return Starlite([])
"""


GENERIC_APP_FACTORY_FILE_CONTENT = """
from starlite import Starlite

def any_name() -> Starlite:
    return Starlite([])
"""

GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION = """
from starlite import Starlite

def any_name() -> "Starlite":
    return Starlite([])
"""


@contextmanager
def create_app_file(
    file: Union[str, Path], directory: Optional[Union[str, Path]] = None, content: Optional[str] = None
) -> Generator[Path, None, None]:
    base = Path.cwd()
    if directory:
        base = base / directory
        base.mkdir()

    tmp_app_file = base / file
    tmp_app_file.write_text(
        content
        or """
from starlite import Starlite
app = Starlite([])
"""
    )

    try:
        yield tmp_app_file
    finally:
        if directory:
            shutil.rmtree(directory)
        else:
            tmp_app_file.unlink()


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


def test_get_session_backend() -> None:
    session_middleware = MemoryBackendConfig().middleware
    app = Starlite(
        [],
        middleware=[
            RateLimitConfig(rate_limit=("second", 1)).middleware,
            session_middleware,
        ],
    )

    assert _get_session_backend(app) is session_middleware.kwargs["backend"]


@pytest.mark.parametrize("env_name,attr_name", [("STARLITE_DEBUG", "debug"), ("STARLITE_RELOAD", "reload")])
@pytest.mark.parametrize(
    "env_value,expected_value",
    [("true", True), ("True", True), ("1", True), ("0", False), (None, False)],
)
def test_starlite_env_from_env_booleans(
    monkeypatch: MonkeyPatch,
    app_file: Path,
    attr_name: str,
    env_name: str,
    env_value: Optional[str],
    expected_value: bool,
) -> None:
    if env_value is not None:
        monkeypatch.setenv(env_name, env_value)

    env = StarliteEnv.from_env(f"{app_file.stem}:app")

    assert getattr(env, attr_name) is expected_value
    assert isinstance(env.app, Starlite)


def test_starlite_env_from_env_port(monkeypatch: MonkeyPatch, app_file: Path) -> None:
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.port is None

    monkeypatch.setenv("STARLITE_PORT", "7000")
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.port == 7000


def test_starlite_env_from_env_host(monkeypatch: MonkeyPatch, app_file: Path) -> None:
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.host is None

    monkeypatch.setenv("STARLITE_HOST", "0.0.0.0")
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.host == "0.0.0.0"


@pytest.mark.parametrize(
    "file_content",
    [
        APP_FILE_CONTENT,
        CREATE_APP_FILE_CONTENT,
        GENERIC_APP_FACTORY_FILE_CONTENT,
        GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION,
    ],
)
@pytest.mark.parametrize("path", AUTODISCOVER_PATHS)
def test_env_from_env_autodiscover_from_files(path: str, file_content: str) -> None:
    directory = None
    if "/" in path:
        directory, path = path.split("/", 1)

    with create_app_file(path, directory, content=file_content) as tmp_file_path:
        env = StarliteEnv.from_env(None)

    assert isinstance(env.app, Starlite)
    assert env.app_path == f"{_path_to_dotted_path(tmp_file_path.relative_to(Path.cwd()))}:app"


def test_autodiscover_not_found() -> None:
    with pytest.raises(StarliteCLIException):
        _autodiscover_app(None)


def test_info_command(mocker: MockerFixture, runner: CliRunner, app_file: Path) -> None:
    mock = mocker.patch("starlite.cli._show_app_info")
    result = runner.invoke(cli_command, ["info"])

    assert result.exception is None
    mock.assert_called_once()


@pytest.mark.parametrize("set_in_env", [True, False])
@pytest.mark.parametrize("custom_app_file", [Path("my_app.py"), None])
@pytest.mark.parametrize("host", ["0.0.0.0", None])
@pytest.mark.parametrize("port", [8081, None])
@pytest.mark.parametrize("reload", [True, False, None])
def test_run_command(
    mocker: MockerFixture,
    runner: CliRunner,
    monkeypatch: MonkeyPatch,
    mock_uvicorn_run: MagicMock,
    reload: Optional[bool],
    port: Optional[int],
    host: Optional[str],
    custom_app_file: Optional[Path],
    set_in_env: bool,
) -> None:
    mock_show_app_info = mocker.patch("starlite.cli._show_app_info")

    args = ["run"]

    if custom_app_file:
        args[0:0] = ["--app", f"{custom_app_file.stem}:app"]

    if reload:
        if set_in_env:
            monkeypatch.setenv("STARLITE_RELOAD", "true")
        else:
            args.append("--reload")
    else:
        reload = False

    if port:
        if set_in_env:
            monkeypatch.setenv("STARLITE_PORT", str(port))
        else:
            args.extend(["--port", str(port)])
    else:
        port = 8000

    if host:
        if set_in_env:
            monkeypatch.setenv("STARLITE_HOST", host)
        else:
            args.extend(["--host", host])
    else:
        host = "127.0.0.1"

    with create_app_file(custom_app_file or "asgi.py") as path:

        result = runner.invoke(cli_command, args)

    assert result.exception is None
    assert result.exit_code == 0

    mock_uvicorn_run.assert_called_once_with(
        f"{path.stem}:app",
        reload=reload,
        port=port,
        host=host,
        factory=False,
    )
    mock_show_app_info.assert_called_once()


@pytest.mark.parametrize(
    "file_name,file_content,factory_name",
    [
        ("_create_app.py", CREATE_APP_FILE_CONTENT, "create_app"),
        ("_generic_app_factory.py", GENERIC_APP_FACTORY_FILE_CONTENT, "any_name"),
        ("_generic_app_factory_string_ann.py", GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION, "any_name"),
    ],
    ids=["create-app", "generic", "generic-string-annotated"],
)
def test_run_command_with_app_factory(
    runner: CliRunner,
    mock_uvicorn_run: MagicMock,
    file_name: str,
    file_content: str,
    factory_name: str,
    monkeypatch: MonkeyPatch,
) -> None:
    from starlite import cli

    monkeypatch.setattr(cli, "AUTODISCOVER_PATHS", [file_name])
    with create_app_file(file_name, content=file_content) as path:
        result = runner.invoke(cli_command, "run")

    assert result.exception is None
    assert result.exit_code == 0

    mock_uvicorn_run.assert_called_once_with(
        f"{path.stem}:{factory_name}",
        reload=False,
        port=8000,
        host="127.0.0.1",
        factory=True,
    )


def test_run_command_force_debug(app_file: Path, mocker: MockerFixture, runner: CliRunner) -> None:
    mock_app = MagicMock()
    mocker.patch(
        "starlite.cli._autodiscover_app",
        return_value=DiscoveredApp(app=mock_app, app_path=str(app_file), is_factory=False),
    )

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


def test_register_commands_from_entrypoint(mocker: MockerFixture, runner: CliRunner, app_file: Path) -> None:
    mock_command_callback = MagicMock()

    @group()
    def custom_group() -> None:
        pass

    @custom_group.command()
    def custom_command(app: Starlite) -> None:
        mock_command_callback()

    mock_entry_point = MagicMock()
    mock_entry_point.load = lambda: custom_group
    if sys.version_info < (3, 10):
        mocker.patch("importlib_metadata.entry_points", return_value=[mock_entry_point])
    else:
        mocker.patch("importlib.metadata.entry_points", return_value=[mock_entry_point])
    cli_command = importlib.reload(starlite.cli).cli

    result = runner.invoke(cli_command, f"--app={app_file.stem}:app custom-group custom-command")

    assert result.exit_code == 0
    mock_command_callback.assert_called_once_with()
