from typing import Any

from litestar import Litestar, Request, get, post
from litestar.middleware.session.server_side import ServerSideSessionConfig

session_config = ServerSideSessionConfig()


@post("/login", sync_to_thread=False)
def login(request: Request) -> None:
    request.set_session({"user": "alice"})


@get("/whoami", sync_to_thread=False)
def whoami(request: Request) -> dict[str, Any]:
    return {"user": request.session.get("user")}


app = Litestar(
    route_handlers=[login, whoami],
    middleware=[session_config.middleware],
)
