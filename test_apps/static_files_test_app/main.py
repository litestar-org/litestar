from pathlib import Path
from typing import Dict

from litestar import Litestar, get
from litestar.static_files import create_static_files_router


@get("/")
async def handler() -> Dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[
        create_static_files_router(directories=[Path(__file__).parent / "public"], path="/", html_mode=True)
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
