import importlib
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

try:
    from rich_click import group
except ImportError:
    from click import group

import litestar.cli._utils
import litestar.cli.main
from litestar import Litestar
from litestar.cli._utils import _format_is_enabled
from litestar.cli.main import litestar_group as cli_command

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


def test_info_command(mocker: "MockerFixture", runner: "CliRunner", app_file: "Path") -> None:
    mock = mocker.patch("litestar.cli.commands.core.show_app_info")
    result = runner.invoke(cli_command, ["info"])

    assert result.exception is None
    mock.assert_called_once()


def test_register_commands_from_entrypoint(mocker: "MockerFixture", runner: "CliRunner", app_file: "Path") -> None:
    mock_command_callback = MagicMock()

    @group()
    def custom_group() -> None:
        pass

    @custom_group.command()
    def custom_command(app: Litestar) -> None:
        mock_command_callback()

    mock_entry_point = MagicMock()
    mock_entry_point.load = lambda: custom_group
    if sys.version_info < (3, 10):
        mocker.patch("importlib_metadata.entry_points", return_value=[mock_entry_point])
    else:
        mocker.patch("importlib.metadata.entry_points", return_value=[mock_entry_point])

    importlib.reload(litestar.cli._utils)
    cli_command = importlib.reload(litestar.cli.main).litestar_group

    result = runner.invoke(cli_command, f"--app={app_file.stem}:app custom-group custom-command")

    assert result.exit_code == 0
    mock_command_callback.assert_called_once_with()
