from __future__ import annotations

from mimetypes import guess_type
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from litestar.enums import MediaType
from litestar.response.base import Response
from litestar.status_codes import HTTP_200_OK

__all__ = ("TemplateResponse",)


if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.template import TemplateEngineProtocol
    from litestar.types import ResponseCookies


class TemplateResponse(Response[bytes]):
    """Template-based response, rendering a given template into a bytes string."""

    def __init__(
        self,
        template_name: str,
        *,
        template_engine: TemplateEngineProtocol,
        context: dict[str, Any],
        status_code: int = HTTP_200_OK,
        background: BackgroundTask | BackgroundTasks | None = None,
        headers: dict[str, Any] | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        media_type: MediaType | str = MediaType.HTML,
    ) -> None:
        """Handle the rendering of a given template into a bytes string.

        Args:
            template_name: Path-like name for the template to be rendered, e.g. ``index.html``.
            template_engine: The template engine class to use to render the response.
            status_code: A value for the response HTTP status code.
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to ``None``.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: Content encoding
            media_type: A string or member of the :class:`MediaType <.enums.MediaType>` enum. If not set, try to infer
                the media type based on the template name. If this fails, fall back to ``text/plain``.
        """
        if media_type == MediaType.JSON:  # we assume this is the default
            suffixes = PurePath(template_name).suffixes
            for suffix in suffixes:
                if _type := guess_type("name" + suffix)[0]:
                    media_type = _type
                    break
            else:
                media_type = MediaType.TEXT

        template = template_engine.get_template(template_name)
        super().__init__(
            background=background,
            content=template.render(**context),
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=media_type,
            status_code=status_code,
        )
