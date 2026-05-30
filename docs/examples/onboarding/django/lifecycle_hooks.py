import logging

from litestar import Litestar, Request, get

logger = logging.getLogger(__name__)


def attach_user(request: Request) -> None:
    request.state["user"] = request.headers.get("x-user", "anonymous")


def log_status(request: Request) -> None:
    """``after_response`` runs after the response body is sent — good for logging."""
    logger.info("request to %s by %s", request.url.path, request.state.get("user"))


@get("/hello")
async def hello(request: Request) -> dict[str, str]:
    return {"user": request.state["user"]}


app = Litestar(
    route_handlers=[hello],
    before_request=attach_user,
    after_response=log_status,
)
