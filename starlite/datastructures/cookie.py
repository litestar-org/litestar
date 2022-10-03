from http.cookies import SimpleCookie
from typing import Any, Optional

from pydantic import BaseModel
from typing_extensions import Literal


class Cookie(BaseModel):
    """Container class for defining a cookie using the 'Set-Cookie' header.

    See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie for more details regarding this header.
    """

    key: str
    """Key for the cookie."""
    value: Optional[str] = None
    """Value for the cookie, if none given defaults to empty string."""
    max_age: Optional[int] = None
    """Maximal age of the cookie before its invalidated."""
    expires: Optional[int] = None
    """Expiration date as unix MS timestamp."""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: Optional[str] = None
    """Domain for which the cookie is valid."""
    secure: Optional[bool] = None
    """Https is required for the cookie."""
    httponly: Optional[bool] = None
    """Forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""
    description: Optional[str] = None
    """Description of the response cookie header for OpenAPI documentation"""
    documentation_only: bool = False
    """Defines the Cookie instance as for OpenAPI documentation purpose only"""

    def to_header(self, **kwargs: Any) -> str:
        """Return a string representation suitable to be sent as HTTP headers.

        Args:
            **kwargs: Passed to [SimpleCookie][http.cookies.SimpleCookie]
        """

        simple_cookie: SimpleCookie = SimpleCookie()
        simple_cookie[self.key] = self.value or ""
        if self.max_age:
            simple_cookie[self.key]["max-age"] = self.max_age
        cookie_dict = self.dict()
        for key in ("expires", "path", "domain", "secure", "httponly", "samesite"):
            value = cookie_dict[key]
            if value is not None:
                simple_cookie[self.key][key] = value
        return simple_cookie.output(**kwargs).strip()
