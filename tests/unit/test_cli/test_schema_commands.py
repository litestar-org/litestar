from __future__ import annotations

from json import dumps as json_dumps
from typing import TYPE_CHECKING, Callable

import pytest
from yaml import dump as dump_yaml

from litestar.cli.commands.schema import _generate_openapi_schema
from litestar.cli.main import litestar_group as cli_command

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from click.testing import CliRunner
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("filename", ("", "custom.json", "custom.yaml", "custom.yml"))
def test_openapi_schema_command(
    runner: CliRunner, mocker: MockerFixture, monkeypatch: MonkeyPatch, filename: str
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_bytes = mocker.patch("pathlib.Path.write_bytes")
    command = "schema openapi"

    from test_apps.openapi_test_app.main import app as openapi_test_app

    assert openapi_test_app.openapi_schema
    schema = openapi_test_app.openapi_schema.to_schema()

    expected_content = json_dumps(schema, indent=4).encode()
    if filename:
        command += f" --output {filename}"
        if filename.endswith(("yaml", "yml")):
            expected_content = dump_yaml(schema, default_flow_style=False, encoding="utf-8")

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    mock_path_write_bytes.assert_called_once_with(expected_content)


@pytest.mark.parametrize("suffix", ("json", "yaml", "yml"))
def test_schema_export_with_examples(suffix: str, create_module: Callable[[str], ModuleType], tmp_path: Path) -> None:
    module = create_module(
        """
from datetime import datetime
from litestar import Litestar, get
from litestar.openapi import OpenAPIConfig

@get()
async def something(date: datetime) -> None:
    return None

app = Litestar([something], openapi_config=OpenAPIConfig('example', '0.0.1', True))
    """
    )
    pth = tmp_path / f"openapi.{suffix}"
    _generate_openapi_schema(module.app, pth)
    assert pth.read_text()


@pytest.mark.parametrize(
    "namespace, filename", (("Custom", ""), ("", "custom_specs.ts"), ("Custom", "custom_specs.ts"))
)
def test_openapi_typescript_command(
    runner: CliRunner, mocker: MockerFixture, monkeypatch: MonkeyPatch, filename: str, namespace: str
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "test_apps.openapi_test_app.main:app")
    mock_path_write_text = mocker.patch("pathlib.Path.write_text")
    command = "schema typescript"

    if namespace:
        command += f" --namespace {namespace}"
    if filename:
        command += f" --output {filename}"

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    assert mock_path_write_text.called


@pytest.mark.parametrize(
    "namespace, filename", (("Custom", ""), ("", "custom_specs.ts"), ("Custom", "custom_specs.ts"))
)
def test_openapi_typescript_command_without_jsbeautifier(
    runner: CliRunner, mocker: MockerFixture, monkeypatch: MonkeyPatch, filename: str, namespace: str
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "test_apps.openapi_test_app.main:app")
    mocker.patch("litestar.cli.commands.schema.JSBEAUTIFIER_INSTALLED", False)
    mock_path_write_text = mocker.patch("pathlib.Path.write_text")
    command = "schema typescript"

    if namespace:
        command += f" --namespace {namespace}"
    if filename:
        command += f" --output {filename}"

    result = runner.invoke(cli_command, command)
    assert result.exit_code == 0
    assert mock_path_write_text.called
