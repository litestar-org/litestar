from litestar.cli.main import litestar_group  # pragma: no cover


def run_cli() -> None:
    """Application Entrypoint."""
    litestar_group()  # pragma: no cover


if __name__ == "__main__":
    run_cli()
