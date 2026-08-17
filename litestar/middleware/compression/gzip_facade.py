from __future__ import annotations

from gzip import GzipFile
from typing import TYPE_CHECKING, Any, Literal

from litestar.enums import CompressionEncoding
from litestar.middleware.compression.facade import CompressionFacade

if TYPE_CHECKING:
    from io import BytesIO


class GzipCompression(CompressionFacade):
    __slots__ = ("buffer", "compression_encoding", "compressor")

    encoding = CompressionEncoding.GZIP

    def __init__(
        self,
        buffer: BytesIO,
        compression_encoding: Literal[CompressionEncoding.GZIP] | str,
        backend_config: Any = None,
    ) -> None:
        backend_config = backend_config or {}
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        self.compressor = GzipFile(mode="wb", fileobj=buffer, compresslevel=backend_config.get("compress_level", 9))

    def write(self, body: bytes | bytearray, final: bool = False) -> None:
        data = bytes(body)
        self.compressor.write(data)
        self.compressor.flush()

    def close(self) -> None:
        self.compressor.close()
