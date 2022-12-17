from typing import List, Literal, Optional, Set, Union

from pydantic import BaseModel

from starlite.types import Method


class CSRFConfig(BaseModel):
    """Configuration for CSRF (Cross Site Request Forgery) protection.

    To enable CSRF protection, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor using
    the 'csrf_config' key.
    """

    secret: str
    """A string that is used to create an HMAC to sign the CSRF token."""
    cookie_name: str = "csrftoken"
    """The CSRF cookie name."""
    cookie_path: str = "/"
    """The CSRF cookie path."""
    header_name: str = "x-csrftoken"
    """The header that will be expected in each request."""
    cookie_secure: bool = False
    """A boolean value indicating whether to set the `Secure` attribute on the cookie."""
    cookie_httponly: bool = False
    """A boolean value indicating whether to set the `HttpOnly` attribute on the cookie."""
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    """The value to set in the `SameSite` attribute of the cookie."""
    cookie_domain: Optional[str] = None
    """Specifies which hosts can receive the cookie."""
    safe_methods: Set[Method] = {"GET", "HEAD"}
    """A set of "safe methods" that can set the cookie."""
    exclude: Optional[Union[str, List[str]]] = None
    """A pattern or list of patterns to skip in the CSRF middleware."""
    exclude_from_csrf_key: str = "exclude_from_csrf"
    """An identifier to use on routes to disable CSRF for a particular route."""
