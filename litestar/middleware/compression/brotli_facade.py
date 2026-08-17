from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from litestar.enums import CompressionEncoding
from litestar.exceptions import MissingDependencyException
from litestar.middleware.compression.facade import CompressionFacade

try:
    from brotli import MODE_FONT, MODE_GENERIC, MODE_TEXT, Compressor
except ImportError as e:
    raise MissingDependencyException("brotli") from e


if TYPE_CHECKING:
    from io import BytesIO


class BrotliCompression(CompressionFacade):
    __slots__ = ("buffer", "compression_encoding", "compressor")

    encoding = CompressionEncoding.BROTLI

    def __init__(
        self,
        buffer: BytesIO,
        compression_encoding: Literal[CompressionEncoding.BROTLI] | str,
        backend_config: Any = None,
    ) -> None:
        backend_config = backend_config or {}
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        modes: dict[Literal["generic", "text", "font"], int] = {
            "text": int(MODE_TEXT),
            "font": int(MODE_FONT),
            "generic": int(MODE_GENERIC),
        }
        self.compressor = Compressor(
            quality=backend_config.get("quality", 5),
            mode=modes[backend_config.get("mode", "text")],
            lgwin=backend_config.get("lgwin", 22),
            lgblock=backend_config.get("lgblock", 0),
        )

    def write(self, body: bytes | bytearray, final: bool = False) -> None:
        self.buffer.write(self.compressor.process(body))
        self.buffer.write(self.compressor.flush())

    def close(self) -> None:
        self.buffer.write(self.compressor.finish())
