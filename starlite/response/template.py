from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from starlite.enums import MediaType
from starlite.response.base import Response
from starlite.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.template import TemplateEngineProtocol
    from starlite.types import ResponseCookies


class TemplateResponse(Response[bytes]):
    def __init__(
        self,
        template_name: str,
        *,
        template_engine: "TemplateEngineProtocol",
        context: Dict[str, Any],
        status_code: int = HTTP_200_OK,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
    ) -> None:
        """Handles the rendering of a given template into a bytes string.

        Args:
            template_name: Path-like name for the template to be rendered, e.g. "index.html".
            template_engine: The template engine class to use to render the response.
            status_code: A value for the response HTTP status code.
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of [Cookie][starlite.datastructures.Cookie] instances to be set under the response 'Set-Cookie' header.
        """
        template = template_engine.get_template(template_name)
        super().__init__(
            background=background,
            content=template.render(**context),
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=MediaType.HTML,
            status_code=status_code,
        )
