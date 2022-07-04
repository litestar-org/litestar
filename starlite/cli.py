import typer
import importlib.metadata

from cookiecutter.main import cookiecutter

cli = typer.Typer(
    chain=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
)


def version_callback(version: bool) -> None:
    if version:
        print(f"Current CLI Version: {importlib.metadata.version('starlite')}")
        raise typer.Exit()

@cli.command()
def create():
    cookiecutter('https://github.com/audreyr/cookiecutter-pypackage.git')

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
