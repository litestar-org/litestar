from typing import TYPE_CHECKING, Any, Dict, cast

from pydantic import BaseModel, conint
from typing_extensions import Literal

if TYPE_CHECKING:

    from starlite.types import ASGIApp


class CompressionConfig(BaseModel):
    """Configuration for response compression.

    To enable response compression, pass an instance of this class to
    the [Starlite][starlite.app.Starlite] constructor using the
    'compression_config' key.
    """

    backend: Literal["gzip", "brotli"]
    """
        Literal of "gzip" or "brotli"
    """
    minimum_size: conint(gt=0) = 500  # type: ignore[valid-type]
    """
        Minimum response size (bytes) to enable compression, affects all backends.
    """
    gzip_compress_level: conint(ge=0, le=9) = 9  # type: ignore[valid-type]
    """
        Range [0-9], see [official docs](https://docs.python.org/3/library/gzip.html).
    """
    brotli_quality: conint(ge=0, le=11) = 5  # type: ignore[valid-type]
    """
        Range [0-11], Controls the compression-speed vs compression-density tradeoff. The higher the quality, the slower
        the compression.
    """
    brotli_mode: Literal["generic", "text", "font"] = "text"
    """
        MODE_GENERIC, MODE_TEXT (for UTF-8 format text input, default) or MODE_FONT (for WOFF 2.0).
    """
    brotli_lgwin: conint(ge=10, le=24) = 22  # type: ignore[valid-type]
    """
        Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
    """
    brotli_lgblock: Literal[0, 16, 17, 18, 19, 20, 21, 22, 23, 24] = 0
    """
        Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will be set based
        on the quality. Defaults to 0.
    """
    brotli_gzip_fallback: bool = True
    """
        Use GZIP if Brotli not supported.
    """

    def dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Returns a dictionary representation of the CompressionConfig.

        Returns:
            dictionary representation of the selected CompressionConfig.  Only columns for the selected backend are included
        """
        brotli_keys = {
            "minimum_size",
            "brotli_quality",
            "brotli_mode",
            "brotli_lgwin",
            "brotli_lgblock",
            "brotli_gzip_fallback",
        }
        gzip_keys = {"minimum_size", "gzip_compress_level"}
        if self.backend == "gzip":
            kwargs["include"] = gzip_keys
        elif self.backend == "brotli":
            kwargs["include"] = brotli_keys

        return super().dict(*args, **kwargs)

    def to_middleware(self, app: "ASGIApp") -> "ASGIApp":
        """Creates a middleware instance from the config.

        Args:
            app: The [Starlite][starlite.app.Starlite] App instance.

        Returns:
            A middleware instance
        """
        if self.backend == "gzip":
            from starlite.middleware.compression.gzip import (  # pylint: disable=import-outside-toplevel
                GZipMiddleware,
            )

            return cast("ASGIApp", GZipMiddleware(app=app, **self.dict()))

        from starlite.middleware.compression.brotli import (  # pylint: disable=import-outside-toplevel
            BrotliMiddleware,
        )

        return BrotliMiddleware(app=app, **self.dict())
