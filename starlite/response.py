from typing import Any, Dict, Optional, Union

from orjson import dumps
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

from starlite.enums import MediaType, OpenAPIMediaType
from starlite.exceptions import ImproperlyConfiguredException


class Response(StarletteResponse):
    def __init__(
        self,
        content: Any = None,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[Union[MediaType, OpenAPIMediaType, str]] = None,
        background: BackgroundTask = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    def render(self, content: Any) -> bytes:
        try:
            if self.media_type in [MediaType.JSON, OpenAPIMediaType.OPENAPI_JSON]:
                if isinstance(content, BaseModel):
                    return content.json().encode("utf-8")
                return dumps(content)
            if self.media_type == OpenAPIMediaType.OPENAPI_YAML:
                import yaml  # pylint: disable=import-outside-toplevel

                content_dict = content.dict(exclude_none=True) if isinstance(content, BaseModel) else content
                return yaml.dump(content_dict, default_flow_style=False).encode("utf-8")
            return super().render(content)
        except (AttributeError, ValueError, TypeError) as e:
            raise ImproperlyConfiguredException("Unable to serialize response content") from e
        except ImportError as e:  # pragma: no cover
            raise ImproperlyConfiguredException(
                "pyyaml is not installed\n\nTo generate yaml based openapi responses, "
                "please install it or change the media_type to JSON."
            ) from e


__all__ = ["Response", "StreamingResponse", "FileResponse", "RedirectResponse"]
