import importlib.metadata
from enum import Enum
from typing import List
from pick import pick

import typer
from cookiecutter.main import cookiecutter

cli = typer.Typer(
    chain=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
)


class ProjectTemplates(str, Enum):
    minimal = "https://github.com/JeromeK13/starlite-minimal-starter.git"
    other = "someother repo"


def version_callback(version: bool) -> None:
    if version:
        print(f"Current CLI Version: {importlib.metadata.version('starlite')}")
        raise typer.Exit()


@cli.command()
def create(
    project_template: ProjectTemplates = typer.Option(
        ..., "--project-template", "-p", help="Select which project structure should be generated", prompt=True
    ),
):
    pick(ProjectTemplates)
    


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


if __name__ == "__main__":
    cli()
