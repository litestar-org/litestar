# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import keyword
import re
from pathlib import Path

from click import Path as ClickPath

try:
    import rich_click as click
except ImportError:
    import click  # type: ignore[no-redef]

from litestar.cli._utils import LitestarCLIException, LitestarGroup

__all__ = ("create_controller", "create_group")

_CAMEL_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")


@click.group(cls=LitestarGroup, name="create")
def create_group() -> None:
    """Scaffold Litestar application components."""


def _validate_controller_name(name: str) -> None:
    """Reject names that cannot become a Python class or module."""
    if not name or any(character.isspace() for character in name):
        raise LitestarCLIException(f"Invalid controller name {name!r}: expected a non-empty name without spaces.")
    if name[0].isdigit():
        raise LitestarCLIException(f"Invalid controller name {name!r}: names must not start with a digit.")
    if keyword.iskeyword(name) or not name.isidentifier():
        raise LitestarCLIException(
            f"Invalid controller name {name!r}: expected a valid Python identifier "
            "(letters, digits, and underscores; cannot be a reserved keyword)."
        )


def _to_snake_case(name: str) -> str:
    """Convert ``Widget`` or ``UserProfile`` to ``widget`` / ``user_profile``."""
    with_boundaries = _CAMEL_BOUNDARY_1.sub(r"\1_\2", name)
    return _CAMEL_BOUNDARY_2.sub(r"\1_\2", with_boundaries).lower()


def _to_pascal_case(name: str) -> str:
    """Convert a validated identifier to PascalCase."""
    return "".join(part.capitalize() for part in _to_snake_case(name).split("_") if part)


def _controller_source(class_name: str, route_path: str, snake_name: str) -> str:
    """Return source for a runnable ``Controller`` subclass."""
    return f'''from litestar import Controller, get


class {class_name}(Controller):
    """Example controller scaffolded by ``litestar create controller``."""

    path = "{route_path}"

    @get()
    async def get_{snake_name}(self) -> dict[str, str]:
        """Return an example response."""
        return {{"message": "Hello from {class_name}"}}
'''


def _test_source(class_name: str, module_name: str, route_path: str, snake_name: str) -> str:
    """Return a ``TestClient`` test for the scaffolded controller."""
    return f'''from litestar import Litestar
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from {module_name} import {class_name}

app = Litestar(route_handlers=[{class_name}])


def test_get_{snake_name}() -> None:
    """The example route responds with HTTP 200."""
    with TestClient(app=app) as client:
        response = client.get("{route_path}")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {{"message": "Hello from {class_name}"}}
'''


def _resolve_output_dir(output: Path | None) -> Path:
    """Return the directory that will receive the generated files."""
    directory = Path.cwd() if output is None else output
    if directory.exists() and not directory.is_dir():
        raise LitestarCLIException(f"Output path is not a directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_file(path: Path, content: str, *, force: bool) -> None:
    """Write ``content`` to ``path``, refusing to overwrite unless ``force`` is set."""
    if path.exists() and not force:
        raise LitestarCLIException(f"File already exists: {path}. Pass --force to overwrite.")
    path.write_text(content, encoding="utf-8")


@create_group.command("controller")  # type: ignore[untyped-decorator]
@click.argument("name")
@click.option(
    "--output",
    "-o",
    type=ClickPath(path_type=Path),
    default=None,
    help="Directory to write the controller file into (defaults to cwd)",
)
@click.option(
    "--path",
    type=str,
    default=None,
    help="Base route path for the controller (defaults to /<name-lower>)",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
def create_controller(name: str, output: Path | None, path: str | None, force: bool) -> None:
    """Scaffold a new Litestar Controller class."""
    _validate_controller_name(name)
    snake_name = _to_snake_case(name)
    class_name = f"{_to_pascal_case(name)}Controller"
    route_path = path if path is not None else f"/{name.lower()}"
    module_name = f"{snake_name}_controller"

    directory = _resolve_output_dir(output)
    controller_path = directory / f"{module_name}.py"
    test_path = directory / f"test_{module_name}.py"

    if not force:
        existing = [file_path for file_path in (controller_path, test_path) if file_path.exists()]
        if existing:
            joined = ", ".join(str(file_path) for file_path in existing)
            raise LitestarCLIException(f"File already exists: {joined}. Pass --force to overwrite.")

    _write_file(
        controller_path,
        _controller_source(class_name, route_path, snake_name),
        force=force,
    )
    _write_file(
        test_path,
        _test_source(class_name, module_name, route_path, snake_name),
        force=force,
    )
    click.echo(f"Created controller {controller_path}")
    click.echo(f"Created test {test_path}")
