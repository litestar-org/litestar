from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from starlite import Starlite, asgi

if TYPE_CHECKING:
    from starlette.requests import Request


async def index(request: "Request") -> JSONResponse:
    """A generic starlette handler."""
    return JSONResponse({"forwarded_path": request.url.path})


starlette_app = asgi(path="/some/sub-path", is_mount=True)(
    Starlette(
        debug=True,
        routes=[
            Route("/", index),
            Route("/abc/", index),
            Route("/123/another/sub-path/", index),
        ],
    )
)


app = Starlite(route_handlers=[starlette_app])
