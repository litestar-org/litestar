from litestar import Litestar, get
from litestar.logging.config import LoggingConfig
from litestar.middleware.logging import LoggingMiddleware


@get("/")
async def my_handler() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[my_handler],
    logging_config=LoggingConfig(),
    middleware=[
        LoggingMiddleware(
            request_log_fields=("query", "body"),  # only log query and body fields
        )
    ],
)
