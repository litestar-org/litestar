from json import dumps
from pathlib import Path

from click import group, option
from jsbeautifier import Beautifier
from yaml import dump as dump_yaml

from starlite import Starlite
from starlite.cli.utils import StarliteCLIException, StarliteGroup
from starlite.openapi.typescript_converter.converter import (
    convert_openapi_to_typescript,
)

beautifier = Beautifier()


@group(cls=StarliteGroup, name="openapi")
def openapi_group() -> None:
    """Manage server-side openapi."""


@openapi_group.command("schema")
@option("--output", help="output file path", type=str, default="openapi_schema.json")
def generate_openapi_schema(app: Starlite, output: str) -> None:
    """Generate an OpenAPI Schema."""
    if not app.openapi_schema:
        raise StarliteCLIException("Starlite application does not have an OpenAPI schema")

    if output.lower().endswith(("yml", "yaml")):
        content = dump_yaml(app.openapi_schema.dict(by_alias=True, exclude_none=True), default_flow_style=False)
    else:
        content = dumps(app.openapi_schema.dict(by_alias=True, exclude_none=True), indent=4)

    try:
        Path(output).write_bytes(content.encode())
    except OSError as e:
        raise StarliteCLIException(f"failed to write schema to path {output}") from e


@openapi_group.command("typescript")
@option("--output", help="output file path", type=str, default="api-specs.ts")
@option("--namespace", help="namespace to use for the typescript specs", type=str, default="API")
def generate_typescript_specs(app: Starlite, output: str, namespace: str) -> None:
    """Generate TypeScript specs from the OpenAPI schema."""
    if not app.openapi_schema:
        raise StarliteCLIException("Starlite application does not have an OpenAPI schema")

    try:
        specs = convert_openapi_to_typescript(app.openapi_schema, namespace)
        beautified_output = beautifier.beautify(specs.write())
        Path(output).write_bytes(beautified_output.encode())
    except OSError as e:
        raise StarliteCLIException(f"failed to write schema to path {output}") from e
