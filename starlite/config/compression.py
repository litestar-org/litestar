from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Union, cast

from pydantic import BaseModel, conint, validator
from typing_extensions import Literal

from starlite.enums import CompressionBackend
from starlite.utils import import_string

if TYPE_CHECKING:
    from typing import Type

    from starlette.types import ASGIApp

    from starlite.middleware.base import MiddlewareProtocol


class CompressionEncoding(str, Enum):
    """An Enum for supported compression encodings."""

    GZIP = "gzip"
    BROTLI = "br"


class BrotliMode(str, Enum):
    """Enumerates the available brotli compression optimization modes."""

    GENERIC = "generic"
    TEXT = "text"
    FONT = "font"


class CompressionConfig(BaseModel):
    """Configuration for response compression.

    To enable response compression, pass an instance of this class to
    the [Starlite][starlite.app.Starlite] constructor using the
    'compression_config' key.
    """

    backend: Union[CompressionBackend]
    """
        [CompressionBackend][starlite.enums.CompressionBackend] or dotted path for
        compression backend to import.
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
    brotli_mode: Union[BrotliMode, str] = BrotliMode.TEXT
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

    @validator("brotli_mode", pre=True, always=True)
    def brotli_mode_must_be_valid(cls, v: Union[BrotliMode, str]) -> BrotliMode:  # pylint: disable=no-self-argument
        """Compression Backend Validation.

        Args:
            v (CompressionBackend|str): Holds the selected compression backend

        Raises:
            ValueError: Value is not a valid compression backend

        Returns:
            _type_: CompressionBackend
        """
        if isinstance(v, str):
            try:
                v = BrotliMode[v.upper()]
            except KeyError as e:
                raise ValueError(f"{v} is not a valid compression optimization mode") from e
        return v

    def dict(self, *args, **kwargs) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        """Returns a dictionary representation of the CompressionConfig.

        Returns:
            Dict[str, Any]: dictionary representation of the selected CompressionConfig.  Only columns for the selected backend are included
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
        if self.backend == CompressionBackend.GZIP:
            kwargs["include"] = gzip_keys
        elif self.backend == CompressionBackend.BROTLI:
            kwargs["include"] = brotli_keys
        else:
            kwargs["include"] = brotli_keys.union(gzip_keys)

        return super().dict(*args, **kwargs)

    def to_middleware(self, app: "ASGIApp") -> "MiddlewareProtocol":
        """Creates a middleware instance from the config.

        Args:
            app: The [Starlite][starlite.app.Starlite] App instance.

        Returns:
            A middleware instance
        """
        if self.backend == CompressionBackend.GZIP:
            handler = cast(
                "Type[MiddlewareProtocol]", import_string("starlite.middleware.compression.gzip.GZipMiddleware")
            )
        else:
            handler = cast(
                "Type[MiddlewareProtocol]", import_string("starlite.middleware.compression.brotli.BrotliMiddleware")
            )
        return handler(app=app, **self.dict())
