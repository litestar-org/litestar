from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union
from urllib.parse import quote

from starlite.constants import REDIRECT_STATUS_CODES
from starlite.enums import MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response.base import Response
from starlite.status_codes import HTTP_307_TEMPORARY_REDIRECT

if TYPE_CHECKING:

    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.types import ResponseCookies


class RedirectResponse(Response[Any]):
    """A redirect response."""

    def __init__(
        self,
        url: str,
        *,
        status_code: Literal[301, 302, 303, 307, 308] = HTTP_307_TEMPORARY_REDIRECT,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
    ) -> None:
        """Initialize the response.

        Args:
            url: A url to redirect to.
            status_code: An HTTP status code. The status code should be one of 301, 302, 303, 307 or 308,
                otherwise an exception will be raised. .
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of [Cookie][starlite.datastructures.Cookie] instances to be set under the response 'Set-Cookie' header.
            encoding: The encoding to be used for the response headers.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If status code is not a redirect status code.
        """
        if status_code not in REDIRECT_STATUS_CODES:
            raise ImproperlyConfiguredException(
                f"{status_code} is not a valid for this response. "
                f"Redirect responses should have one of "
                f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
            )
        super().__init__(
            background=background,
            content=b"",
            cookies=cookies,
            headers={**(headers or {}), "location": quote(url, safe="/#%[]=:;$&()+,!?*@'~")},
            media_type=MediaType.TEXT,
            status_code=status_code,
            encoding=encoding,
        )
