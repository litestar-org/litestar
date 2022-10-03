from typing import TYPE_CHECKING, Any, Dict, Optional

from starlite_multipart.datastructures import UploadFile as MultipartUploadFile

from starlite.openapi.enums import OpenAPIType

if TYPE_CHECKING:
    from pydantic.fields import ModelField


class UploadFile(MultipartUploadFile):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any], field: Optional["ModelField"]) -> None:
        """Creates a pydantic JSON schema.

        Args:
            field_schema: The schema being generated for the field.
            field: the model class field.

        Returns:
            None
        """
        if field:
            field_schema.update({"type": OpenAPIType.STRING.value, "contentMediaType": "application/octet-stream"})

    def __repr__(self) -> str:
        return f"{self.filename} - {self.content_type}"
