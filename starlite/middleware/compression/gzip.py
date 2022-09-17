from typing import TYPE_CHECKING

from starlette.middleware.gzip import GZipMiddleware as StarletteGzipMiddleware

if TYPE_CHECKING:
    from starlite.types import ASGIApp


class GZipMiddleware(StarletteGzipMiddleware):
    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int = 400,
        gzip_compress_level: int = 9,
    ) -> None:
        """GZIP Compression middleware for Starlite.

        This is a wrapper around the Starlette GZipMiddleware.
        It converts the Starlite parameters into the expected Gzip parameters.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum size for the response body to affect compression.
            gzip_compress_level: The gzip compression level, value is in range from 1 to 9.
        """
        super().__init__(app, minimum_size=minimum_size, compresslevel=gzip_compress_level)  # type: ignore[arg-type]
