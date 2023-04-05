from json import dumps
from pathlib import Path

from click import Path as ClickPath
from click import group, option
from jsbeautifier import Beautifier
from yaml import dump as dump_yaml

from litestar import Litestar
from litestar._openapi.typescript_converter.converter import (
    convert_openapi_to_typescript,
)
from litestar.cli._utils import LitestarCLIException, LitestarGroup

__all__ = ("generate_openapi_schema", "generate_typescript_specs", "schema_group")


beautifier = Beautifier()


@group(cls=LitestarGroup, name="schema")
def schema_group() -> None:
    """Manage server-side OpenAPI schemas."""


@schema_group.command("openapi")
@option(
    "--output",
    help="output file path",
    type=ClickPath(dir_okay=False, path_type=Path),
    default=Path("openapi_schema.json"),
    show_default=True,
)
def generate_openapi_schema(app: Litestar, output: Path) -> None:
    """Generate an OpenAPI Schema."""
    if not app.openapi_schema:  # pragma: no cover
        raise LitestarCLIException("Litestar application does not have an OpenAPI schema")

    if output.suffix in (".yml", ".yaml"):
        content = dump_yaml(app.openapi_schema.to_schema(), default_flow_style=False)
    else:
        content = dumps(app.openapi_schema.to_schema(), indent=4)

    try:
        output.write_text(content)
    except OSError as e:  # pragma: no cover
        raise LitestarCLIException(f"failed to write schema to path {output}") from e


@schema_group.command("typescript")
@option(
    "--output",
    help="output file path",
    type=ClickPath(dir_okay=False, path_type=Path),
    default=Path("api-specs.ts"),
    show_default=True,
)
@option("--namespace", help="namespace to use for the typescript specs", type=str, default="API")
def generate_typescript_specs(app: Litestar, output: Path, namespace: str) -> None:
    """Generate TypeScript specs from the OpenAPI schema."""
    if not app.openapi_schema:  # pragma: no cover
        raise LitestarCLIException("Litestar application does not have an OpenAPI schema")

    try:
        specs = convert_openapi_to_typescript(app.openapi_schema, namespace)
        beautified_output = beautifier.beautify(specs.write())
        output.write_text(beautified_output)
    except OSError as e:  # pragma: no cover
        raise LitestarCLIException(f"failed to write schema to path {output}") from e
