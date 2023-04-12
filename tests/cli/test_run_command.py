from pathlib import Path
from typing import Callable, List, Optional
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
from pytest_mock import MockerFixture

from starlite.cli.main import starlite_group as cli_command
from starlite.cli.utils import LoadedApp
from tests.cli import (
    CREATE_APP_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION,
)
from tests.cli.conftest import CreateAppFileFixture


@pytest.mark.parametrize("set_in_env", [True, False])
@pytest.mark.parametrize("custom_app_file", [Path("my_app.py"), None])
@pytest.mark.parametrize("host", ["0.0.0.0", None])
@pytest.mark.parametrize("port", [8081, None])
@pytest.mark.parametrize("reload", [True, False, None])
def test_run_command(
    mocker: MockerFixture,
    runner: CliRunner,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    reload: Optional[bool],
    port: Optional[int],
    host: Optional[str],
    custom_app_file: Optional[Path],
    create_app_file: CreateAppFileFixture,
    set_in_env: bool,
) -> None:
    mock_show_app_info = mocker.patch("starlite.cli.commands.core.show_app_info")

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

    path = create_app_file(custom_app_file or "asgi.py")

    result = runner.invoke(cli_command, args)

    assert result.exception is None
    assert result.exit_code == 0

    expected_args = ["uvicorn", f"{path.stem}:app", f"--host={host}", f"--port={port}"]
    if reload:
        expected_args.append("--reload")

    mock_subprocess_run.assert_called_once()
    assert sorted(mock_subprocess_run.call_args_list[0].args[0]) == sorted(expected_args)
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
def test_run_command_with_autodiscover_app_factory(
    runner: CliRunner,
    mock_subprocess_run: MagicMock,
    file_name: str,
    file_content: str,
    factory_name: str,
    patch_autodiscovery_paths: Callable[[List[str]], None],
    create_app_file: CreateAppFileFixture,
) -> None:
    patch_autodiscovery_paths([file_name])
    path = create_app_file(file_name, content=file_content)
    result = runner.invoke(cli_command, "run")

    assert result.exception is None
    assert result.exit_code == 0

    expected_args = ["uvicorn", f"{path.stem}:{factory_name}", "--host=127.0.0.1", "--port=8000", "--factory"]
    mock_subprocess_run.assert_called_once()
    assert sorted(mock_subprocess_run.call_args_list[0].args[0]) == sorted(expected_args)


def test_run_command_with_app_factory(
    runner: CliRunner,
    mock_subprocess_run: MagicMock,
    create_app_file: CreateAppFileFixture,
) -> None:
    path = create_app_file("_create_app_with_path.py", content=CREATE_APP_FILE_CONTENT)
    app_path = f"{path.stem}:create_app"
    result = runner.invoke(cli_command, ["--app", app_path, "run"])

    assert result.exception is None
    assert result.exit_code == 0

    expected_args = ["uvicorn", str(app_path), "--host=127.0.0.1", "--port=8000", "--factory"]
    mock_subprocess_run.assert_called_once()
    assert sorted(mock_subprocess_run.call_args_list[0].args[0]) == sorted(expected_args)


def test_run_command_force_debug(app_file: Path, mocker: MockerFixture, runner: CliRunner) -> None:
    mock_app = MagicMock()
    mocker.patch(
        "starlite.cli.utils._autodiscover_app",
        return_value=LoadedApp(app=mock_app, app_path=str(app_file), is_factory=False),
    )

    runner.invoke(cli_command, "run --debug")

    assert mock_app.debug is True
