from __future__ import annotations

from mimetypes import guess_type
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import ASGIResponse, Response
from litestar.status_codes import HTTP_200_OK
from litestar.utils.helpers import filter_cookies, get_enum_string_value

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures import Cookie
    from litestar.types import ResponseCookies, TypeEncodersMap

__all__ = ("TemplateResponse",)


class TemplateResponse(Response[bytes]):
    """Template-based response, rendering a given template into a bytes string."""

    __slots__ = (
        "template_name",
        "context",
    )

    def __init__(
        self,
        template_name: str,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        context: dict[str, Any] | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: dict[str, Any] | None = None,
        media_type: MediaType | str | None = None,
        status_code: int = HTTP_200_OK,
    ) -> None:
        """Handle the rendering of a given template into a bytes string.

        Args:
            template_name: Path-like name for the template to be rendered, e.g. ``index.html``.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to ``None``.
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: Content encoding
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            media_type: A string or member of the :class:`MediaType <.enums.MediaType>` enum. If not set, try to infer
                the media type based on the template name. If this fails, fall back to ``text/plain``.
            status_code: A value for the response HTTP status code.
            template_engine: The template engine class to use to render the response.
        """
        super().__init__(
            background=background,
            content=b"",
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=media_type,
            status_code=status_code,
        )
        self.context = context or {}
        self.template_name = template_name

    def create_template_context(self, request: Request) -> dict[str, Any]:
        """Create a context object for the template.

        Args:
            request: A :class:`Request <.connection.Request>` instance.

        Returns:
            A dictionary holding the template context
        """
        csrf_token = request.scope.get("_csrf_token", "")
        return {
            **self.context,
            "request": request,
            "csrf_input": f'<input type="hidden" name="_csrf_token" value="{csrf_token}" />',
        }

    def to_asgi_response(
        self,
        *,
        app: Litestar,
        background: BackgroundTask | BackgroundTasks | None,
        cookies: list[Cookie] | None,
        encoded_headers: list[tuple[bytes, bytes]] | None,
        headers: dict[str, str] | None,
        is_head_response: bool,
        media_type: MediaType | str | None,
        request: Request,
        status_code: int | None,
        type_encoders: TypeEncodersMap | None,
    ) -> ASGIResponse:
        if not app.template_engine:
            raise ImproperlyConfiguredException("Template engine is not configured")

        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else filter_cookies(self.cookies, cookies)

        media_type = self.media_type or media_type if media_type != "application/json" else None
        if not media_type:
            suffixes = PurePath(self.template_name).suffixes
            for suffix in suffixes:
                if _type := guess_type("name" + suffix)[0]:
                    media_type = _type
                    break
            else:
                media_type = MediaType.TEXT

        media_type = get_enum_string_value(media_type)

        template = app.template_engine.get_template(self.template_name)
        context = self.create_template_context(request)
        body = template.render(**context).encode(self.encoding)

        return ASGIResponse(
            background=self.background or background,
            body=body,
            content_length=None,
            cookies=cookies,
            encoded_headers=encoded_headers or [],
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )
