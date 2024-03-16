import logging
from typing import TYPE_CHECKING, Any

from litestar import Litestar, Request, get
from litestar.datastructures import State
from litestar.di import Provide

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


def set_state_on_startup(app: Litestar) -> None:
    """Startup and shutdown hooks can receive `State` as a keyword arg."""
    app.state.value = "abc123"


def middleware_factory(*, app: "ASGIApp") -> "ASGIApp":
    """A middleware can access application state via `scope`."""

    async def my_middleware(scope: "Scope", receive: "Receive", send: "Send") -> None:
        state = scope["app"].state
        logger.info("state value in middleware: %s", state.value)
        await app(scope, receive, send)

    return my_middleware


async def my_dependency(state: State) -> Any:
    """Dependencies can receive state via injection."""
    logger.info("state value in dependency: %s", state.value)


@get(
    "/",
    dependencies={"dep": Provide(my_dependency)},
    middleware=[middleware_factory],
    sync_to_thread=False,
)
def get_handler(state: State, request: Request, dep: Any) -> None:
    """Handlers can receive state via injection."""
    logger.info("state value in handler from `State`: %s", state.value)
    logger.info("state value in handler from `Request`: %s", request.app.state.value)


app = Litestar(route_handlers=[get_handler], on_startup=[set_state_on_startup])
