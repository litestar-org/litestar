from starlite import Starlite, get
from starlite.logging.config import LoggingConfig
from starlite.middleware.logging import LoggingMiddlewareConfig


@get("/")
async def handler() -> dict[str, str]:
    return {"hello": "world"}


logging_middleware_config = LoggingMiddlewareConfig()

app = Starlite(
    route_handlers=[handler],
    logging_config=LoggingConfig(),
    middleware=[logging_middleware_config.middleware],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
