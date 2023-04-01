from typing import TYPE_CHECKING

from litestar import Litestar, Response, asgi

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
    response = Response(content={"forwarded_path": scope["path"]})
    await response(scope, receive, send)


app = Litestar(route_handlers=[my_asgi_app])
