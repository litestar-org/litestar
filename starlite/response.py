from typing import Any, Dict, Optional, Union, cast

import yaml
from openapi_schema_pydantic import OpenAPI
from orjson import OPT_INDENT_2, OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.responses import Response as StarletteResponse
from starlette.types import Receive, Scope, Send

from starlite.enums import MediaType, OpenAPIMediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.template import AbstractTemplateEngine


class Response(StarletteResponse):
    def __init__(
        self,
        content: Any,
        status_code: int,
        media_type: Union[MediaType, OpenAPIMediaType, str],
        background: Optional[BackgroundTask] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers or {},
            media_type=media_type,
            background=background,  # type: ignore
        )

    @staticmethod
    def serializer(value: Any) -> Dict[str, Any]:
        """
        Serializer hook for orjson to handle pydantic models.

        This method can be overridden to extend json serialization
        """
        if isinstance(value, BaseModel):
            return value.dict()
        raise TypeError  # pragma: no cover

    def render(self, content: Any) -> bytes:
        """Renders content into bytes"""
        try:
            if self.media_type == MediaType.JSON:
                return dumps(content, default=self.serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
            if isinstance(content, OpenAPI):
                content_dict = content.dict(by_alias=True, exclude_none=True)
                if self.media_type == OpenAPIMediaType.OPENAPI_YAML:
                    encoded = yaml.dump(content_dict, default_flow_style=False).encode("utf-8")
                    return cast(bytes, encoded)
                return dumps(content_dict, option=OPT_INDENT_2 | OPT_OMIT_MICROSECONDS)
            return super().render(content)
        except (AttributeError, ValueError, TypeError) as e:
            raise ImproperlyConfiguredException("Unable to serialize response content") from e


class TemplateResponse(StarletteResponse):
    def __init__(
        self,
        context: Dict[str, Any],
        template_name: str,
        template_engine: AbstractTemplateEngine,
        status_code: int,
        background: Optional[BackgroundTask] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.template = template_engine.get_template(template_name)
        self.context = context
        content = self.template.render(**context)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers or {},
            media_type=MediaType.HTML,
            background=background,  # type: ignore
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # code from https://github.com/encode/starlette/blob/master/starlette/templating.py
        request = self.context.get("request", {})
        extensions = request.get("extensions", {})
        if "http.response.template" in extensions:  # pragma: no cover
            await send(
                {
                    "type": "http.response.template",
                    "template": self.template,
                    "context": self.context,
                }
            )
        await super().__call__(scope, receive, send)
