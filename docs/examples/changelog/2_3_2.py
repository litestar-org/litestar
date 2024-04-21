from litestar import Litestar
from litestar import post
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