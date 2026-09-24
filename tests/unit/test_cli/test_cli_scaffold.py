from __future__ import annotations

import ast
import importlib.util
import sys
from typing import TYPE_CHECKING

import pytest

from litestar import Litestar
from litestar.cli._utils import LitestarCLIException
from litestar.cli.commands.scaffold import _write_file
from litestar.cli.main import litestar_group as cli_command
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner


def test_create_controller_writes_valid_python(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(cli_command, ["create", "controller", "Widget", "--output", str(tmp_path)])

    assert result.exception is None
    assert result.exit_code == 0

    controller_path = tmp_path / "widget_controller.py"
    test_path = tmp_path / "test_widget_controller.py"
    assert controller_path.is_file()
    assert test_path.is_file()
    assert str(controller_path) in result.output
    assert str(test_path) in result.output

    controller_source = controller_path.read_text(encoding="utf-8")
    ast.parse(controller_source)
    ast.parse(test_path.read_text(encoding="utf-8"))
    assert 'path = "/widget"' in controller_source
    assert "class WidgetController(Controller):" in controller_source

    module_name = "widget_controller_scaffold"
    spec = importlib.util.spec_from_file_location(module_name, controller_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    app = Litestar(route_handlers=[module.WidgetController])
    with TestClient(app=app) as client:
        response = client.get("/widget")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"message": "Hello from WidgetController"}


def test_create_controller_respects_path(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        cli_command,
        ["create", "controller", "Widget", "--output", str(tmp_path), "--path", "/widgets"],
    )

    assert result.exception is None
    assert result.exit_code == 0
    source = (tmp_path / "widget_controller.py").read_text(encoding="utf-8")
    assert 'path = "/widgets"' in source
    test_source = (tmp_path / "test_widget_controller.py").read_text(encoding="utf-8")
    assert 'client.get("/widgets")' in test_source


def test_create_controller_rejects_invalid_name(runner: CliRunner, tmp_path: Path) -> None:
    for name in ("", "my controller", "1widget", "not-a-name"):
        result = runner.invoke(cli_command, ["create", "controller", name, "--output", str(tmp_path)])
        assert result.exit_code != 0
        assert result.exception is not None
        assert "Invalid controller name" in result.output
        assert "Traceback" not in result.output

    assert not any(tmp_path.iterdir())


def test_create_controller_refuses_to_overwrite_without_force(runner: CliRunner, tmp_path: Path) -> None:
    first = runner.invoke(cli_command, ["create", "controller", "Widget", "--output", str(tmp_path)])
    assert first.exit_code == 0
    original = (tmp_path / "widget_controller.py").read_text(encoding="utf-8")

    second = runner.invoke(cli_command, ["create", "controller", "Widget", "--output", str(tmp_path)])
    assert second.exit_code != 0
    assert second.exception is not None
    assert "already exists" in second.output
    assert "Traceback" not in second.output
    assert (tmp_path / "widget_controller.py").read_text(encoding="utf-8") == original


def test_create_controller_force_overwrites(runner: CliRunner, tmp_path: Path) -> None:
    controller_path = tmp_path / "widget_controller.py"
    test_path = tmp_path / "test_widget_controller.py"
    controller_path.write_text("stale controller\n", encoding="utf-8")
    test_path.write_text("stale test\n", encoding="utf-8")

    result = runner.invoke(
        cli_command,
        ["create", "controller", "Widget", "--output", str(tmp_path), "--force"],
    )

    assert result.exception is None
    assert result.exit_code == 0
    assert "stale" not in controller_path.read_text(encoding="utf-8")
    assert "class WidgetController(Controller):" in controller_path.read_text(encoding="utf-8")
    assert "stale" not in test_path.read_text(encoding="utf-8")


def test_create_controller_rejects_output_that_is_a_file(runner: CliRunner, tmp_path: Path) -> None:
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("not a directory\n", encoding="utf-8")

    result = runner.invoke(cli_command, ["create", "controller", "Widget", "--output", str(output_file)])

    assert result.exit_code != 0
    assert result.exception is not None
    assert "not a directory" in result.output
    assert output_file.name in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "widget_controller.py").exists()


def test_write_file_refuses_existing_file_without_force(tmp_path: Path) -> None:
    target = tmp_path / "existing.py"
    target.write_text("keep\n", encoding="utf-8")

    with pytest.raises(LitestarCLIException, match="already exists"):
        _write_file(target, "replaced\n", force=False)

    assert target.read_text(encoding="utf-8") == "keep\n"
