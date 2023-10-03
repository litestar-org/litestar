import textwrap

from click.testing import CliRunner

from litestar.cli._utils import LitestarGroup
from tests.unit.test_cli.conftest import CreateAppFileFixture


def test_basic_command(runner: CliRunner, create_app_file: CreateAppFileFixture, root_command: LitestarGroup) -> None:
    app_file_content = textwrap.dedent(
        """
    from litestar import Litestar
    from litestar.plugins import CLIPluginProtocol

    class CLIPlugin(CLIPluginProtocol):
        def on_cli_init(self, cli):
            @cli.command()
            def foo(app: Litestar):
                print(f"App is loaded: {app is not None}")

    app = Litestar(plugins=[CLIPlugin()])
    """
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "foo"])

    assert not result.exception
    assert "App is loaded: True" in result.output
