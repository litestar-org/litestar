from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Literal

from litestar.enums import CompressionEncoding
from litestar.exceptions import MissingDependencyException
from litestar.middleware.compression.facade import CompressionFacade

if sys.version_info >= (3, 14):
    from compression import zstd
else:
    try:
        from backports import zstd
    except ImportError as e:
        raise MissingDependencyException("backports.zstd", extra="zstd") from e

if TYPE_CHECKING:
    from io import BytesIO

    from litestar.config.compression import CompressionConfig


class ZstdCompression(CompressionFacade):
    __slots__ = ("buffer", "compression_encoding", "compressor")

    encoding = CompressionEncoding("zstd")
    upper_bound = zstd.CompressionParameter.compression_level.bounds()[1]

    def __init__(
        self,
        buffer: BytesIO,
        compression_encoding: Literal["zstd"] | str,
        config: CompressionConfig,
    ) -> None:
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        self.compressor = zstd.ZstdCompressor(level=config.zstd_compress_level)

    def write(
        self,
        body: bytes | bytearray,
        final: bool = False,
    ) -> None:
        if not final:
            self.buffer.write(self.compressor.compress(body, mode=zstd.ZstdCompressor.FLUSH_BLOCK))
        else:
            self.buffer.write(self.compressor.compress(body, mode=zstd.ZstdCompressor.FLUSH_FRAME))

    def close(self) -> None:
        if self.compressor.last_mode != zstd.ZstdCompressor.FLUSH_FRAME:
            self.buffer.write(self.compressor.flush())
