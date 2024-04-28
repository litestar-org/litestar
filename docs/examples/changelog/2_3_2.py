from litestar import Litestar, post
from litestar.static_files import StaticFilesConfig


@post("/uploads")
async def handler() -> None:
    pass


app = Litestar(
    [handler],
    static_files_config=[
        StaticFilesConfig(directories=["uploads"], path="/uploads"),
    ],
)
