import pytest
from click.testing import CliRunner

from litestar.cli.main import litestar_group as cli_command


@pytest.mark.parametrize("option", ["--version", "-V"])
def test_suggest_version(option: str, runner: CliRunner) -> None:
    result = runner.invoke(cli_command, option)

    assert "Did you mean command `version`?" in result.output
