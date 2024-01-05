from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from io import BytesIO

    from litestar.config.compression import CompressionConfig
    from litestar.enums import CompressionEncoding


class CompressionFacade(Protocol):
    """A unified facade offering a uniform interface for different compression libraries."""

    __slots__ = ("compressor", "buffer", "compression_encoding")

    def __init__(self, buffer: BytesIO, compression_encoding: CompressionEncoding, config: CompressionConfig) -> None:
        """Initialize ``CompressionFacade``.

        Args:
            buffer: A bytes IO buffer to write the compressed data into.
            compression_encoding: The compression encoding used.
            config: The app compression config.
        """
        ...

    def write(self, body: bytes) -> None:
        """Write compressed bytes.

        Args:
            body: Message body to process

        Returns:
            None
        """
        ...

    def close(self) -> None:
        """Close the compression stream.

        Returns:
            None
        """
        ...
