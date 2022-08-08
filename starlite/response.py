from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

import yaml
from orjson import OPT_INDENT_2, OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel
from pydantic_openapi_schema.v3_1_0.open_api import OpenAPI
from starlette.responses import Response as StarletteResponse
from starlette.status import HTTP_204_NO_CONTENT

from starlite.enums import MediaType, OpenAPIMediaType
from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlette.background import BackgroundTask

    from starlite.template import TemplateEngineProtocol


class Response(StarletteResponse):
    def __init__(
        self,
        content: Any,
        status_code: int,
        media_type: Union[MediaType, OpenAPIMediaType, str],
        background: Optional["BackgroundTask"] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers or {},
            media_type=media_type,
            background=cast("BackgroundTask", background),
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
        if self.status_code == HTTP_204_NO_CONTENT and content is None:
            return b""

        try:
            if self.media_type == MediaType.JSON:
                return dumps(content, default=self.serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
            if isinstance(content, OpenAPI):
                content_dict = content.dict(by_alias=True, exclude_none=True)
                if self.media_type == OpenAPIMediaType.OPENAPI_YAML:
                    encoded = yaml.dump(content_dict, default_flow_style=False).encode("utf-8")
                    return cast("bytes", encoded)
                return dumps(content_dict, option=OPT_INDENT_2 | OPT_OMIT_MICROSECONDS)
            return super().render(content)
        except (AttributeError, ValueError, TypeError) as e:
            raise ImproperlyConfiguredException("Unable to serialize response content") from e


class TemplateResponse(Response):
    def __init__(
        self,
        context: Optional[Dict[str, Any]],
        template_name: str,
        template_engine: "TemplateEngineProtocol",
        status_code: int,
        background: Optional["BackgroundTask"] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        context = context or {}
        template = template_engine.get_template(template_name)
        content = template.render(**context or {})
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=MediaType.HTML,
            background=background,
        )
