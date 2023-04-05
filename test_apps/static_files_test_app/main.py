from pathlib import Path

from starlite import Starlite, get
from starlite.static_files.config import StaticFilesConfig


@get("/")
async def handler() -> dict[str, str]:
    return {"hello": "world"}


app = Starlite(
    route_handlers=[],
    static_files_config=[
        StaticFilesConfig(directories=[Path(__file__).parent / "public"], path="/", html_mode=True),
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
