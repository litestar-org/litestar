from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING, Any, Dict, Optional

from anyio.to_thread import run_sync

from starlite.constants import ONE_MEGABYTE
from starlite.openapi.enums import OpenAPIType

if TYPE_CHECKING:
    from pydantic.fields import ModelField


class UploadFile:
    """Representation of a file upload, modifying the pydantic schema."""

    __slots__ = ("filename", "file", "content_type", "headers")

    def __init__(
        self,
        content_type: str,
        filename: str,
        file_data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        max_spool_size: int = ONE_MEGABYTE,
    ) -> None:
        """Upload file in-memory container.

        Args:
            content_type: Content type for the file.
            filename: The filename.
            file_data: File data.
            headers: Any attached headers.
            max_spool_size: The size above which the temporary file will be rolled to disk.
        """
        self.filename = filename
        self.content_type = content_type
        self.file = SpooledTemporaryFile(max_size=max_spool_size)  # pylint: disable=consider-using-with
        self.headers = headers or {}

        if file_data:
            self.file.write(file_data)
            self.file.seek(0)

    @property
    def rolled_to_disk(self) -> bool:
        """Determine whether the spooled file exceeded the rolled-to-disk threshold and is no longer in memory.

        Returns:
            A boolean flag
        """
        return getattr(self.file, "_rolled", False)

    async def write(self, data: bytes) -> int:
        """Proxy for data writing.

        Args:
            data: Byte string to write.

        Returns:
            None
        """
        if self.rolled_to_disk:
            return await run_sync(self.file.write, data)
        return self.file.write(data)

    async def read(self, size: int = -1) -> bytes:
        """Proxy for data reading.

        Args:
            size: position from which to read.

        Returns:
            Byte string.
        """
        if self.rolled_to_disk:
            return await run_sync(self.file.read, size)
        return self.file.read(size)

    async def seek(self, offset: int) -> int:
        """Async proxy for file seek.

        Args:
            offset: start position..

        Returns:
            None.
        """
        if self.rolled_to_disk:
            return await run_sync(self.file.seek, offset)
        return self.file.seek(offset)

    async def close(self) -> None:
        """Async proxy for file close.

        Returns:
            None.
        """
        if self.rolled_to_disk:
            return await run_sync(self.file.close)
        return self.file.close()

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
