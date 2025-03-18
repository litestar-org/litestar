from typing import Dict

from litestar import Litestar, Request, get
from litestar.plugins.structlog import StructlogPlugin


@get("/")
async def handler(request: Request) -> Dict[str, str]:
    request.logger.info("Logging in the handler")
    return {"hello": "world"}


app = Litestar(
    route_handlers=[handler],
    plugins=[StructlogPlugin()],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
