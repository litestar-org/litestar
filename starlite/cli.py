import importlib.metadata
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from cookiecutter.main import cookiecutter

# Init CLI
cli = typer.Typer(
    chain=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
)


class ProjectTemplates(str, Enum):
    minimal = "https://github.com/JeromeK13/starlite-minimal-starter.git"


def version_callback(version: bool) -> None:
    """Returns current version of starlite"""
    if version:
        print(f"Current CLI Version: {importlib.metadata.version('starlite')}")
        raise typer.Exit()


@cli.command()
def create(
    project_template: ProjectTemplates = typer.Option(
        ProjectTemplates.minimal,
        "--project-template",
        "-p",
        help="Select preset for generating the project",
        case_sensitive=False,
    ),
    output_dir: Path = typer.Option(
        os.getcwd(), "--output-dir", "-o", help="Directory where the template will be generated", prompt=True
    ),
):
    """Generates project from cookiecutter template"""
    cookiecutter(template=project_template.value, output_dir=output_dir)


@cli.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Get current CLI version",
        is_eager=True,
        callback=version_callback,
    )
) -> None:
    pass
