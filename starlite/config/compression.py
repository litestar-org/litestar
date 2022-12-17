from typing import List, Literal, Optional, Type, Union

from pydantic import BaseModel, conint

from starlite.middleware.compression import CompressionMiddleware


class CompressionConfig(BaseModel):
    """Configuration for response compression.

    To enable response compression, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor
    using the 'compression_config' key.
    """

    backend: Literal["gzip", "brotli"]
    """Literal of "gzip" or "brotli"."""
    minimum_size: conint(gt=0) = 500  # type: ignore[valid-type]
    """Minimum response size (bytes) to enable compression, affects all backends."""
    gzip_compress_level: conint(ge=0, le=9) = 9  # type: ignore[valid-type]
    """Range [0-9], see [official docs](https://docs.python.org/3/library/gzip.html)."""
    brotli_quality: conint(ge=0, le=11) = 5  # type: ignore[valid-type]
    """Range [0-11], Controls the compression-speed vs compression-density tradeoff.

    The higher the quality, the slower the compression.
    """
    brotli_mode: Literal["generic", "text", "font"] = "text"
    """MODE_GENERIC, MODE_TEXT (for UTF-8 format text input, default) or MODE_FONT (for WOFF 2.0)."""
    brotli_lgwin: conint(ge=10, le=24) = 22  # type: ignore[valid-type]
    """Base 2 logarithm of size.

    Range is 10 to 24. Defaults to 22.
    """
    brotli_lgblock: Literal[0, 16, 17, 18, 19, 20, 21, 22, 23, 24] = 0
    """Base 2 logarithm of the maximum input block size.

    Range is 16 to 24. If set to 0, the value will be set based on the quality. Defaults to 0.
    """
    brotli_gzip_fallback: bool = True
    """Use GZIP if Brotli is not supported."""
    middleware_class: Type[CompressionMiddleware] = CompressionMiddleware
    """Middleware class to use, should be a subclass of CompressionMiddleware."""
    exclude: Optional[Union[str, List[str]]] = None
    """A pattern or list of patterns to skip in the compression middleware."""
    exclude_opt_key: Optional[str] = None
    """An identifier to use on routes to disable compression for a particular route."""
