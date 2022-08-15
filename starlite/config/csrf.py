from typing import Optional, Set

from pydantic import BaseModel
from typing_extensions import Literal

from starlite.types import Method


class CSRFConfig(BaseModel):
    """Configuration for CSRF (Cross Site Request Forgery) protection.

    To enable CSRF protection, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'csrf_config' key.
    """

    secret: str
    """A string that is used to create an HMAC to sign the CSRF token"""
    cookie_name: str = "csrftoken"
    """The CSRF cookie name"""
    cookie_path: str = "/"
    """The CSRF cookie path"""
    header_name: str = "x-csrftoken"
    """The header that will be expected in each request"""
    cookie_secure: bool = False
    """A boolean value indicating whether to set the `Secure` attribute on the cookie"""
    cookie_httponly: bool = False
    """A boolean value indicating whether to set the `HttpOnly` attribute on the cookie"""
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    """The value to set in the `SameSite` attribute of the cookie"""
    cookie_domain: Optional[str] = None
    """Specifies which hosts can receive the cookie"""
    safe_methods: Set[Method] = {"GET", "HEAD"}
    """A set of "safe methods" that can set the cookie"""
