from __future__ import annotations

from gzip import GzipFile
from typing import TYPE_CHECKING, Literal

from litestar.enums import CompressionEncoding
from litestar.middleware.compression.facade import CompressionFacade

if TYPE_CHECKING:
    from io import BytesIO

    from litestar.config.compression import CompressionConfig


class GzipCompression(CompressionFacade):
    __slots__ = ("buffer", "compression_encoding", "compressor")

    encoding = CompressionEncoding.GZIP

    def __init__(
        self, buffer: BytesIO, compression_encoding: Literal[CompressionEncoding.GZIP] | str, config: CompressionConfig
    ) -> None:
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        self.compressor = GzipFile(mode="wb", fileobj=buffer, compresslevel=config.gzip_compress_level)

    def write(self, body: bytes | bytearray, final: bool = False) -> None:
        data = bytes(body)
        self.compressor.write(data)
        self.compressor.flush()

    def close(self) -> None:
        self.compressor.close()
