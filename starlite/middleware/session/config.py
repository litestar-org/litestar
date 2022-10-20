from typing import Optional, Type

from pydantic import BaseConfig, BaseModel, PrivateAttr, conint, conlist, constr
from typing_extensions import Literal

from starlite import DefineMiddleware
from starlite.middleware.session.base import BaseSessionMiddleware

from .base import SessionBackend

ONE_DAY_IN_SECONDS = 60 * 60 * 24


class CookieConfig(BaseModel):
    _backend_class: Type[SessionBackend] = PrivateAttr()

    """Configuration for Session middleware cookies."""

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    """
    A secret key to use for generating an encryption key.
    Must have a length of 16 (128 bits), 24 (192 bits) or 32 (256 bits) characters.
    """
    key: constr(min_length=1, max_length=256) = "session"  # type: ignore[valid-type]
    """
    Key to use for the cookie inside the header,
    e.g. `session=<data>` where 'session' is the cookie key and <data> is the session data.

    Notes:
        - If a session cookie exceeds 4KB in size it is split. In this case the key will be of the format
            'session-{segment number}'.
    """
    max_age: conint(ge=1) = ONE_DAY_IN_SECONDS * 14  # type: ignore[valid-type]
    """Maximal age of the cookie before its invalidated."""
    scopes: conlist(Literal["http", "websocket"], min_items=1, max_items=2) = ["http", "websocket"]  # type: ignore[valid-type]
    """Scopes for the middleware - options are 'http' and 'websocket' with the default being both"""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: Optional[str] = None
    """Domain for which the cookie is valid."""
    secure: bool = False
    """Https is required for the cookie."""
    httponly: bool = True
    """Forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from os import urandom

            from starlite import Starlite, Request, get
            from starlite.middleware.session import SessionCookieConfig

            session_config = SessionCookieConfig(secret=urandom(16))


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[session_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(BaseSessionMiddleware, backend=self._backend_class(config=self))
