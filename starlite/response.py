from typing import Any

from orjson import dumps
from pydantic import BaseModel
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

from starlite.enums import MediaType


class Response(StarletteResponse):
    def render(self, content: Any) -> bytes:
        if self.media_type == MediaType.JSON:
            if isinstance(content, BaseModel):
                return content.json().encode("utf-8")
            return dumps(content)
        return super().render(content=content)


__all__ = ["Response", "StreamingResponse", "FileResponse", "RedirectResponse"]
