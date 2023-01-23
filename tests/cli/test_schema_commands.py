from json import dumps as json_dumps
from typing import TYPE_CHECKING

import pytest
from yaml import dump as dump_yaml

from starlite.cli.main import starlite_group as cli_command
from test_apps.openapi_test_app.main import app as openapi_test_app

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("filename", ("", "custom.json", "custom.yaml", "custom.yml"))
def test_openapi_schema_command(
    runner: "CliRunner", mocker: "MockerFixture", monkeypatch: "MonkeyPatch", filename: str
) -> None:
    monkeypatch.setenv("STARLITE_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_text = mocker.patch("pathlib.Path.write_text")
    command = "schema openapi"

    schema = openapi_test_app.openapi_schema.dict(by_alias=True, exclude_none=True)  # type: ignore[union-attr]

    expected_content = json_dumps(schema, indent=4)
    if filename:
        command += f" --output {filename}"
        if filename.endswith(("yaml", "yml")):
            expected_content = dump_yaml(schema, default_flow_style=False)

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    mock_path_write_text.assert_called_once_with(expected_content)


@pytest.mark.parametrize(
    "namespace, filename", (("Custom", ""), ("", "custom_specs.ts"), ("Custom", "custom_specs.ts"))
)
def test_openapi_typescript_command(
    runner: "CliRunner", mocker: "MockerFixture", monkeypatch: "MonkeyPatch", filename: str, namespace: str
) -> None:
    monkeypatch.setenv("STARLITE_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_text = mocker.patch("pathlib.Path.write_text")
    command = "schema typescript"

    if namespace:
        command += f" --namespace {namespace}"
    if filename:
        command += f" --output {filename}"

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    assert mock_path_write_text.called
