from pathlib import Path

from litestar import Litestar
from litestar.static_files import create_static_files_router

ASSETS_DIR = Path(__file__).parent / "assets"


def ensure_assets() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.joinpath("hello.txt").write_text("Hello, world!")


app = Litestar(
    route_handlers=[
        create_static_files_router(path="/static", directories=[ASSETS_DIR]),
    ],
    on_startup=[ensure_assets],
)
