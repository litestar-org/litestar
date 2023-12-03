from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.exceptions import NotFoundException

if TYPE_CHECKING:
    from litestar import MediaType


class OpenAPINotFoundException(NotFoundException):
    """Exception raised when an OpenAPI endpoint is not found."""

    def __init__(self, body: bytes, media_type: MediaType) -> None:
        self.body = body
        self.media_type = media_type
        super().__init__()
