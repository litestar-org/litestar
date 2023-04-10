from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote

from litestar.constants import REDIRECT_ALLOWED_MEDIA_TYPES, REDIRECT_STATUS_CODES
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import Response
from litestar.status_codes import HTTP_307_TEMPORARY_REDIRECT

__all__ = ("RedirectResponse",)


if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.types import ResponseCookies


class RedirectResponse(Response[Any]):
    """A redirect response."""

    def __init__(
        self,
        url: str,
        *,
        status_code: Literal[301, 302, 303, 307, 308] = HTTP_307_TEMPORARY_REDIRECT,
        background: BackgroundTask | BackgroundTasks | None = None,
        headers: dict[str, Any] | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        media_type: str | MediaType = MediaType.TEXT,
    ) -> None:
        """Initialize the response.

        Args:
            url: A url to redirect to.
            status_code: An HTTP status code. The status code should be one of 301, 302, 303, 307 or 308,
                otherwise an exception will be raised.
            background: A background task or tasks to be run after the response is sent.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            media_type: A value for the response ``Content-Type`` header.


        Raises:
            ImproperlyConfiguredException: Either if status code is not a redirect status code or media type is not supported.
        """
        if status_code not in REDIRECT_STATUS_CODES:
            raise ImproperlyConfiguredException(
                f"{status_code} is not a valid for this response. "
                f"Redirect responses should have one of "
                f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
            )
        if media_type not in REDIRECT_ALLOWED_MEDIA_TYPES:
            raise ImproperlyConfiguredException(
                f"{media_type} media type is not supported yet. "
                f"Media type should be one of "
                f"the following values: {', '.join([str(s) for s in REDIRECT_ALLOWED_MEDIA_TYPES])}"
            )
        super().__init__(
            background=background,
            content=b"",
            cookies=cookies,
            headers={**(headers or {}), "location": quote(url, safe="/#%[]=:;$&()+,!?*@'~")},
            media_type=media_type,
            status_code=status_code,
            encoding=encoding,
        )
