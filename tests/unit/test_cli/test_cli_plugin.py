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
