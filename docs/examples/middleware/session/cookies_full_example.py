from os import urandom
from typing import Dict

from starlite import Request, Starlite, delete, get, post
from starlite.middleware.session.client_side import CookieBackendConfig

# we initialize to config with a 16 byte key, i.e. 128 a bit key.
# in real world usage we should inject the secret from the environment
session_config = CookieBackendConfig(secret=urandom(16))  # type: ignore[arg-type]


@get("/session")
def check_session_handler(request: Request) -> Dict[str, bool]:
    """Handler function that accesses request.session."""
    return {"has_session": request.session != {}}


@post("/session")
def create_session_handler(request: Request) -> None:
    """Handler to set the session."""
    if not request.session:
        # value can be a dictionary or pydantic model
        request.set_session({"username": "moishezuchmir"})


@delete("/session")
def delete_session_handler(request: Request) -> None:
    """Handler to clear the session."""
    if request.session:
        request.clear_session()


app = Starlite(
    route_handlers=[check_session_handler, create_session_handler, delete_session_handler],
    middleware=[session_config.middleware],
)
