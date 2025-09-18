from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from litestar.enums import CompressionEncoding
from litestar.exceptions import MissingDependencyException
from litestar.middleware.compression.facade import CompressionFacade

try:
    import zstandard as zstd
except ImportError as e:
    raise MissingDependencyException("zstandard") from e

if TYPE_CHECKING:
    from io import BytesIO

    from litestar.config.compression import CompressionConfig


class ZstdCompression(CompressionFacade):
    __slots__ = ("buffer", "cctx", "compression_encoding", "compressor")

    encoding = CompressionEncoding("zstd")

    def __init__(self, buffer: BytesIO, compression_encoding: Literal["zstd"] | str, config: CompressionConfig) -> None:
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        self.cctx = zstd.ZstdCompressor(level=config.zstd_compress_level)
        self.compressor = self.cctx.stream_writer(buffer)

    def write(self, body: bytes | bytearray, final: bool = False) -> None:
        self.compressor.write(body)
        if final:
            self.compressor.flush(zstd.FLUSH_FRAME)
        else:
            self.compressor.flush(zstd.FLUSH_BLOCK)

    def close(self) -> None:
        self.compressor.flush(zstd.FLUSH_FRAME)
