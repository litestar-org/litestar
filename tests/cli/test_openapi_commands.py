from json import loads as json_loads
from typing import TYPE_CHECKING

import pytest
from yaml import unsafe_load as yaml_loads

from starlite.cli.main import starlite_group as cli_command

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from click.testing import CliRunner
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("filename", ("", "custom.json", "custom.yaml", "custom.yml"))
def test_openapi_schema_command(
    runner: "CliRunner", mocker: "MockerFixture", monkeypatch: "MonkeyPatch", filename: str
) -> None:
    monkeypatch.setenv("STARLITE_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_bytes = mocker.patch("pathlib.Path.write_bytes")
    command = "openapi schema"

    loads = json_loads
    if filename:
        command += f" --output {filename}"
        if filename.endswith(("yaml", "yml")):
            loads = yaml_loads  # type: ignore

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    assert mock_path_write_bytes.called

    assert loads(mock_path_write_bytes.call_args[0][0].decode())


@pytest.mark.parametrize(
    "namespace, filename", (("Custom", ""), ("", "custom_specs.ts"), ("Custom", "custom_specs.ts"))
)
def test_openapi_typescript_command(
    runner: "CliRunner", mocker: "MockerFixture", monkeypatch: "MonkeyPatch", filename: str, namespace: str
) -> None:
    monkeypatch.setenv("STARLITE_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_bytes = mocker.patch("pathlib.Path.write_bytes")
    command = "openapi typescript"

    if namespace:
        command += f" --namespace {namespace}"
    if filename:
        command += f" --output {filename}"

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    assert mock_path_write_bytes.called
