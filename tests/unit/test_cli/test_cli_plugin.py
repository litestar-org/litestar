from click.testing import CliRunner

from litestar.cli._utils import LitestarExtensionGroup
from tests.unit.test_cli.conftest import CreateAppFileFixture

APPLICATION_WITH_CLI_PLUGIN = """
from litestar import Litestar
from litestar.plugins import CLIPluginProtocol

class CLIPlugin(CLIPluginProtocol):
    def on_cli_init(self, cli):
        @cli.command()
        def mycommand(app: Litestar):
            \"\"\"Description of plugin command\"\"\"
            print(f"App is loaded: {app is not None}")

app = Litestar(plugins=[CLIPlugin()])
"""


def test_basic_command(
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarExtensionGroup,
) -> None:
    app_file = create_app_file("command_test_app.py", content=APPLICATION_WITH_CLI_PLUGIN)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "mycommand"])

    assert not result.exception
    assert "App is loaded: True" in result.output


def test_plugin_command_appears_in_help_message(
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarExtensionGroup,
) -> None:
    app_file = create_app_file("command_test_app.py", content=APPLICATION_WITH_CLI_PLUGIN)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "--help"])

    assert not result.exception
    assert "mycommand" in result.output
    assert "Description of plugin command" in result.output


def test_format_help_loads_plugins_before_rendering(
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarExtensionGroup,
) -> None:
    """Test that format_help method correctly loads plugins before rendering help.

    This specifically tests the fix for rich-click where format_help was called
    before _prepare(), causing plugin commands to not appear in help output.
    """
    app_file = create_app_file("format_help_test_app.py", content=APPLICATION_WITH_CLI_PLUGIN)

    # Test by invoking help which internally calls format_help
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "--help"])

    # Ensure the command succeeded
    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    # Verify that plugin commands are included in the help output
    assert "mycommand" in result.output, "Plugin command should appear in help output"
    assert "Description of plugin command" in result.output, "Plugin command description should appear in help output"

    # Additional verification: ensure the plugin command is in the Commands section
    lines = result.output.split("\n")
    commands_section_found = False
    for line in lines:
        if "Commands" in line:
            commands_section_found = True
        if commands_section_found and "mycommand" in line:
            break
    else:
        assert False, "Plugin command not found in Commands section of help output"
