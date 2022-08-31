import logging
from typing import TYPE_CHECKING, Any

from starlette.requests import HTTPConnection

from starlite import Provide, Request, Starlite, State, get

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


def set_state_on_startup(state: State) -> None:
    """Startup and shutdown hooks can receive `State` as a keyword arg."""
    state.value = "abc123"


def middleware_factory(*, app: "ASGIApp") -> "ASGIApp":
    """A middleware can access application state via `scope`."""

    async def my_middleware(scope: "Scope", receive: "Receive", send: "Send") -> None:
        state = HTTPConnection(scope).app.state
        logger.info("state value in middleware: %s", state.value)
        await app(scope, receive, send)

    return my_middleware


def my_dependency(state: State) -> Any:
    """Dependencies can receive state via injection."""
    logger.info("state value in dependency: %s", state.value)


@get("/", dependencies={"dep": Provide(my_dependency)}, middleware=[middleware_factory])
def get_handler(state: State, request: Request, dep: Any) -> None:  # pylint: disable=unused-argument
    """Handlers can receive state via injection."""
    logger.info("state value in handler from `State`: %s", state.value)
    logger.info("state value in handler from `Request`: %s", request.app.state.value)


starlite = Starlite(route_handlers=[get_handler], on_startup=[set_state_on_startup], debug=True)
