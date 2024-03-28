from litestar.cli.main import litestar_group

__all__ = ("run_cli",)


def run_cli() -> None:
    """Application Entrypoint."""
    litestar_group()


if __name__ == "__main__":
    run_cli()
