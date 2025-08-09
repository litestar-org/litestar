from typing import TYPE_CHECKING

import pytest

from litestar.cli._utils import _format_is_enabled
from litestar.cli.main import litestar_group as cli_command
from tests.unit.test_cli import CREATE_APP_FILE_CONTENT
from tests.unit.test_cli.conftest import CreateAppFileFixture

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def test_format_is_enabled() -> None:
    assert _format_is_enabled(0) == "[red]Disabled[/]"
    assert _format_is_enabled(False) == "[red]Disabled[/]"
    assert _format_is_enabled("") == "[red]Disabled[/]"
    assert _format_is_enabled(1) == "[green]Enabled[/]"
    assert _format_is_enabled(True) == "[green]Enabled[/]"
    assert _format_is_enabled("a") == "[green]Enabled[/]"


@pytest.mark.xdist_group("cli_autodiscovery")
def test_info_command(mocker: "MockerFixture", runner: "CliRunner", app_file: "Path") -> None:
    mock = mocker.patch("litestar.cli.commands.core.show_app_info")
    result = runner.invoke(cli_command, ["info"])

    assert result.exception is None
    mock.assert_called_once()


@pytest.mark.xdist_group("cli_autodiscovery")
def test_info_command_with_app_dir(
    mocker: "MockerFixture", runner: "CliRunner", create_app_file: CreateAppFileFixture
) -> None:
    app_file = "main.py"
    app_file_without_extension = app_file.split(".")[0]
    create_app_file(
        file=app_file,
        directory="src",
        content=CREATE_APP_FILE_CONTENT,
        subdir="info_with_app_dir",
        init_content=f"from .{app_file_without_extension} import create_app",
    )
    mock = mocker.patch("litestar.cli.commands.core.show_app_info")
    result = runner.invoke(cli_command, ["--app", "info_with_app_dir:create_app", "--app-dir", "src", "info"])

    assert result.exception is None
    mock.assert_called_once()


@pytest.mark.xdist_group("cli_autodiscovery")
@pytest.mark.parametrize("invalid_app", ["invalid", "info_with_app_dir"])
def test_incorrect_app_argument(
    invalid_app: str, mocker: "MockerFixture", runner: "CliRunner", create_app_file: CreateAppFileFixture
) -> None:
    app_file = "main.py"
    app_file_without_extension = app_file.split(".")[0]

    create_app_file(
        file=app_file,
        directory="src",
        content=CREATE_APP_FILE_CONTENT,
        subdir="info_with_app_dir",
        init_content=f"from .{app_file_without_extension} import create_app",
    )

    mock = mocker.patch("litestar.cli.commands.core.show_app_info")
    result = runner.invoke(cli_command, ["--app", invalid_app, "--app-dir", "src", "info"])

    assert result.exit_code == 1

    mock.assert_not_called()


@pytest.mark.xdist_group("cli_autodiscovery")
def test_invalid_import_in_app_argument(
    runner: "CliRunner", create_app_file: CreateAppFileFixture, tmp_project_dir: "Path"
) -> None:
    app_file = "main.py"

    create_app_file(
        file=app_file,
        content="from something import bar\n" + CREATE_APP_FILE_CONTENT,
    )

    app_dir = str(tmp_project_dir.absolute())

    result = runner.invoke(cli_command, ["--app", "main:create_app", "--app-dir", app_dir, "info"])
    assert isinstance(result.exception, ModuleNotFoundError)
