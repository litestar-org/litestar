from __future__ import annotations

import itertools
from mimetypes import guess_type
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Iterable

from litestar.datastructures.headers import MutableScopeHeaders
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import ASGIResponse, Response
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED
from litestar.utils.deprecation import warn_deprecation
from litestar.utils.helpers import get_enum_string_value

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures import Cookie
    from litestar.template.base import TemplateProtocol
    from litestar.types import (
        ResponseCookies,
        Send,
        TypeEncodersMap,
    )

__all__ = ("Template",)


class ASGITemplateResponse(ASGIResponse):
    """A low-level ASGI response class, rendering a template into the response."""

    __slots__ = ("template", "context", "is_async", "media_type")

    def __init__(
        self,
        *,
        template: TemplateProtocol,
        context: dict[str, Any],
        is_async: bool = False,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        encoding: str = "utf-8",
        headers: dict[str, Any] | Iterable[tuple[str, str]] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
    ) -> None:
        """A low-level ASGI response class.

        Args:
            template: An object adhering to TemplateProtocol to be rendered in the response
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            is_async: Whether the instance of the used templating engine supports async rendering
            background: A background task or a list of background tasks to be executed after the response is sent.
            cookies: The response cookies.
            encoded_headers: The response headers.
            encoding: The response encoding.
            headers: The response headers.
            is_head_response: A boolean indicating if the response is a HEAD response.
            media_type: The response media type.
            status_code: The response status code.
        """

        status_code = status_code or HTTP_200_OK
        self.headers = MutableScopeHeaders()

        if encoded_headers is not None:
            warn_deprecation("3.0", kind="parameter", deprecated_name="encoded_headers", alternative="headers")
            for header_name, header_value in encoded_headers:
                self.headers.add(header_name.decode("latin-1"), header_value.decode("latin-1"))

        if headers is not None:
            for k, v in headers.items() if isinstance(headers, dict) else headers:
                self.headers.add(k, v)  # pyright: ignore

        self.is_async = is_async
        self.template = template
        self.context = context
        self.media_type = media_type

        self.background = background
        self._encoded_cookies = tuple(
            cookie.to_encoded_header() for cookie in (cookies or ()) if not cookie.documentation_only
        )
        self.encoding = encoding
        self.is_head_response = is_head_response
        self.status_code = status_code

    async def prepare_content(self) -> None:
        if self.is_async:
            rendered_template = await self.template.render_async(**self.context)
        else:
            rendered_template = self.template.render(**self.context)

        body = rendered_template.encode(self.encoding)
        content_length = len(body)

        status_allows_body = (
            self.status_code not in {HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED} and self.status_code >= HTTP_200_OK
        )
        media_type = get_enum_string_value(self.media_type or MediaType.JSON)

        if not status_allows_body or self.is_head_response:
            if body and body != b"null":
                raise ImproperlyConfiguredException(
                    "response content is not supported for HEAD responses and responses with a status code "
                    "that does not allow content (304, 204, < 200)"
                )
            self.body = b""
        else:
            self.headers.setdefault(
                "content-type",
                (f"{media_type}; charset={self.encoding}" if media_type.startswith("text/") else media_type),
            )

            if self._should_set_content_length:
                self.headers.setdefault("content-length", str(content_length))

            self.body = body
            self.content_length = content_length

    async def start_response(self, send: Send) -> None:
        """Emit the start event of the response. This event includes the headers and status codes.

        Args:
            send: The ASGI send function.

        Returns:
            None
        """
        await self.prepare_content()
        await super().start_response(send)


class Template(Response[bytes]):
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
        app: Litestar | None,
        request: Request,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        type_encoders: TypeEncodersMap | None = None,
    ) -> ASGIResponse:
        if app is not None:
            warn_deprecation(
                version="2.1",
                deprecated_name="app",
                kind="parameter",
                removal_in="3.0.0",
                alternative="request.app",
            )

        if not request.app.template_engine:
            raise ImproperlyConfiguredException("Template engine is not configured")

        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)

        media_type = self.media_type or media_type
        if not media_type:
            suffixes = PurePath(self.template_name).suffixes
            for suffix in suffixes:
                if _type := guess_type(f"name{suffix}")[0]:
                    media_type = _type
                    break
            else:
                media_type = MediaType.TEXT

        template = request.app.template_engine.get_template(self.template_name)
        context = self.create_template_context(request)

        return ASGITemplateResponse(
            template=template,
            context=context,
            is_async=request.app.template_engine.is_async,
            background=self.background or background,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )
