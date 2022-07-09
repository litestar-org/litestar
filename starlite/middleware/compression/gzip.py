from typing import TYPE_CHECKING

from starlette.middleware.gzip import GZipMiddleware as StarletteGzipMiddleware

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class GZipMiddleware(StarletteGzipMiddleware):
    """GZIP Compression middleware for Starlite

    This is a wrapper around the Starlette GZipMiddleware.
    It converts the Starlite parameters into the expected Gzip parameters.
    """

    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int = 400,
        gzip_compress_level: int = 9,
    ) -> None:
        super().__init__(app, minimum_size=minimum_size, compresslevel=gzip_compress_level)
