from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, Optional

from anyio.to_thread import run_sync

from starlite.openapi.enums import OpenAPIType

if TYPE_CHECKING:
    from pydantic.fields import ModelField


class UploadFile:
    """Representation of a file upload, modifying the pydantic schema."""

    __slots__ = ("filename", "file", "content_type", "headers", "is_in_memory")

    def __init__(
        self,
        filename: str,
        content_type: str,
        headers: Optional[Dict[str, str]] = None,
        spool_max_size: int = 1024 * 1024,
        file: Optional[BinaryIO] = None,
    ) -> None:
        """Upload file container.

        Args:
            filename: The filename.
            content_type: Content type for the file.
            headers: Any attached headers.
            spool_max_size: Max value to allocate for temporary files.
            file: Optional file data.
        """
        self.filename = filename
        self.content_type = content_type
        self.file = file or SpooledTemporaryFile(max_size=spool_max_size)  # pylint: disable=consider-using-with
        self.headers = headers or {}
        self.is_in_memory = not getattr(self.file, "_rolled", True)

    async def write(self, data: bytes) -> None:
        """Async proxy for data writing.

        Args:
            data: Byte string to write.

        Returns:
            None
        """
        if self.is_in_memory:
            self.file.write(data)
        else:
            await run_sync(self.file.write, data)

    async def read(self, size: int = -1) -> bytes:
        """Async proxy for data reading.

        Args:
            size: position from which to read.

        Returns:
            Byte string.
        """
        if self.is_in_memory:
            return self.file.read(size)
        return await run_sync(self.file.read, size)

    async def seek(self, offset: int) -> None:
        """Async proxy for file seek.

        Args:
            offset: start position..

        Returns:
            None.
        """
        if self.is_in_memory:
            self.file.seek(offset)
        else:
            await run_sync(self.file.seek, offset)

    async def close(self) -> None:
        """Async proxy for file close.

        Returns:
            None.
        """
        if self.is_in_memory:
            self.file.close()
        else:
            await run_sync(self.file.close)

    def __repr__(self) -> str:
        return f"{self.filename} - {self.content_type}"

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any], field: Optional["ModelField"]) -> None:
        """Create a pydantic JSON schema.

        Args:
            field_schema: The schema being generated for the field.
            field: the model class field.

        Returns:
            None
        """
        if field:
            field_schema.update(
                {"type": OpenAPIType.STRING.value, "contentMediaType": "application/octet-stream", "format": "binary"}
            )
