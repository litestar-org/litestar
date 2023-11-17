from __future__ import annotations

import itertools
from mimetypes import guess_type
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Iterable

from litestar.constants import SCOPE_STATE_CSRF_TOKEN_KEY
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import ASGIResponse, Response
from litestar.status_codes import HTTP_200_OK
from litestar.utils import get_litestar_scope_state
from litestar.utils.deprecation import warn_deprecation

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures import Cookie
    from litestar.types import ResponseCookies, TypeEncodersMap

__all__ = ("Template",)


class Template(Response[bytes]):
    """Template-based response, rendering a given template into a bytes string."""

    __slots__ = (
        "template_name",
        "template_str",
        "context",
    )

    def __init__(
        self,
        template_name: str | None = None,
        *,
        template_str: str | None = None,
        background: BackgroundTask | BackgroundTasks | None = None,
        context: dict[str, Any] | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: dict[str, Any] | None = None,
        media_type: MediaType | str | None = None,
        status_code: int = HTTP_200_OK,
    ) -> None:
        """Handle the rendering of a given template into a bytes string.

            .. note:: Either ``template_name`` or ``template_str`` must be provided.
                If both are provided, ``template_str`` will be used.

        Args:
            template_name: Path-like name for the template to be rendered, e.g. ``index.html``.
            template_str: A string representing the template, e.g. ``tmpl = "Hello <strong>World</strong>"``.
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
        self.template_str = template_str

    def create_template_context(self, request: Request) -> dict[str, Any]:
        """Create a context object for the template.

        Args:
            request: A :class:`Request <.connection.Request>` instance.

        Returns:
            A dictionary holding the template context
        """
        csrf_token = get_litestar_scope_state(scope=request.scope, key=SCOPE_STATE_CSRF_TOKEN_KEY, default="")
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
        if not media_type and self.template_name:
            suffixes = PurePath(self.template_name).suffixes
            for suffix in suffixes:
                if _type := guess_type(f"name{suffix}")[0]:
                    media_type = _type
                    break
            else:
                media_type = MediaType.TEXT

        if self.template_str is not None:
            body = self._render_from_string(self.template_str, request)
            media_type = media_type or MediaType.HTML
        else:
            if not self.template_name and not self.template_str:
                raise ValueError("Either template_name or template_str must be provided")

            template = request.app.template_engine.get_template(self.template_name)
            context = self.create_template_context(request)
            body = template.render(**context).encode(self.encoding)

        return ASGIResponse(
            background=self.background or background,
            body=body,
            content_length=None,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )

    def _render_from_string(self, template_str: str, request: Request) -> bytes:
        """Render the template from a string.

        Args:
            template_str: A string representing the template.
            request: A :class:`Request <.connection.Request>` instance.

        Returns:
            Rendered content as bytes.
        """
        context = self.create_template_context(request)
        return request.app.template_engine.render_string(template_str, context).encode(self.encoding)  # type: ignore[no-any-return]
