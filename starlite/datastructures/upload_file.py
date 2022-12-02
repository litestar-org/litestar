from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, Optional

from anyio.to_thread import run_sync

from starlite.openapi.enums import OpenAPIType

if TYPE_CHECKING:
    from pydantic.fields import ModelField


class UploadFile:
    """Representation of a file upload, modifying the pydantic schema."""

    __slots__ = ("filename", "file", "content_type", "headers")

    def __init__(
        self,
        filename: str,
        content_type: str,
        headers: Optional[Dict[str, str]] = None,
        file: Optional[BinaryIO] = None,
    ) -> None:
        """Upload file in-memory container.

        Args:
            filename: The filename.
            content_type: Content type for the file.
            headers: Any attached headers.
            file: Optional file data.
        """
        self.filename = filename
        self.content_type = content_type
        self.file = file
        self.headers = headers or {}

    def write(self, data: bytes) -> None:
        """Proxy for data writing.

        Args:
            data: Byte string to write.

        Returns:
            None
        """
        self.file.write(data)

    def read(self, size: int = -1) -> bytes:
        """Proxy for data reading.

        Args:
            size: position from which to read.

        Returns:
            Byte string.
        """
        return self.file.read(size)

    def seek(self, offset: int) -> None:
        """Async proxy for file seek.

        Args:
            offset: start position..

        Returns:
            None.
        """
        self.file.seek(offset)

    def close(self) -> None:
        """Async proxy for file close.

        Returns:
            None.
        """
        self.file.close()

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
