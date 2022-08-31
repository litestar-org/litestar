from typing import TYPE_CHECKING, Dict

from starlette.datastructures import MutableHeaders

from starlite import Starlite, get

if TYPE_CHECKING:
    from starlite.datastructures import State
    from starlite.types import Message


@get("/test")
def handler() -> Dict[str, str]:
    """Example Handler function."""
    return {"key": "value"}


async def before_send_hook_handler(message: "Message", state: "State") -> None:
    """The function will be called on each ASGI message.

    We therefore ensure it runs only on the message start event.
    """
    if message["type"] == "http.response.start":
        headers = MutableHeaders(scope=message)
        headers.append("My Header", state.message)


def on_startup(state: "State") -> None:
    """A function that will populate the app state before any requests are
    received."""
    state.message = "value injected during send"


app = Starlite(route_handlers=[handler], on_startup=[on_startup], before_send=before_send_hook_handler)
