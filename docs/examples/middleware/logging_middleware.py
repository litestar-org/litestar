import logging

from litestar import Litestar, get
from litestar.middleware.logging import LoggingMiddleware


@get("/")
async def my_handler() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[my_handler],
    middleware=[
        LoggingMiddleware(
            logging.getLogger("my.app"),
            request_log_fields=("query", "body"),  # only log query and body fields
        )
    ],
)
