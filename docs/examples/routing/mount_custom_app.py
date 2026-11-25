import json
from typing import TYPE_CHECKING

from litestar import Litestar, asgi
from litestar.response.base import ASGIResponse

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


@asgi("/some/sub-path", is_mount=True)
async def my_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    """
    Args:
        scope: The ASGI connection scope.
        receive: The ASGI receive function.
        send: The ASGI send function.

    Returns:
        None
    """
    body = json.dumps({"forwarded_path": scope["path"]})
    response = ASGIResponse(body=body.encode("utf-8"))
    await response(scope, receive, send)


app = Litestar(route_handlers=[my_asgi_app])
