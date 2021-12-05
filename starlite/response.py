from typing import Any

from pydantic import BaseModel
from starlette.responses import Response as StarletteResponse

from starlite.enums import MediaType


class Response(StarletteResponse):
    def render(self, content: Any) -> bytes:
        if isinstance(content, BaseModel) and self.media_type == MediaType.JSON:
            return content.json().encode("utf-8")
        return super().render(content=content)
