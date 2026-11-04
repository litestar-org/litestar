def run_cli() -> None:
    """Application Entrypoint."""
    try:
        from litestar.cli.main import litestar_group
    except ImportError as e:
        from litestar.exceptions import MissingDependencyException

        raise MissingDependencyException("click", extra="cli") from e

    litestar_group()


if __name__ == "__main__":
    run_cli()
