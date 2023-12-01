from __future__ import annotations

from typing import TYPE_CHECKING

from litestar._openapi.schema_generation import SchemaCreator
from litestar.enums import RequestEncodingType
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.request_body import RequestBody
from litestar.params import BodyKwarg

__all__ = ("RequestBodyFactory",)


if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.dto import AbstractDTO
    from litestar.typing import FieldDefinition


class RequestBodyFactory:
    """Factory for creating a RequestBody instance for a given route handler's data field."""

    def __init__(
        self,
        context: OpenAPIContext,
        handler_id: str,
        resolved_data_dto: type[AbstractDTO] | None,
        data_field: FieldDefinition,
    ) -> None:
        """Initialize the factory.

        Args:
            context: An OpenAPIContext instance.
            handler_id: A handler id string.
            resolved_data_dto: Data DTO type if resolved for the handler.
            data_field: A FieldDefinition instance for the "data" parameter.
        """
        self.context = context
        self.handler_id = handler_id
        self.resolved_data_dto = resolved_data_dto
        self.field_definition = data_field
        self.schema_creator = SchemaCreator.from_openapi_context(context, prefer_alias=True)

    def create_request_body(self) -> RequestBody:
        """Create a RequestBody instance for the given route handler's data field.

        Returns:
            A RequestBody instance.
        """
        media_type: RequestEncodingType | str = RequestEncodingType.JSON
        if (
            isinstance(self.field_definition.kwarg_definition, BodyKwarg)
            and self.field_definition.kwarg_definition.media_type
        ):
            media_type = self.field_definition.kwarg_definition.media_type

        if self.resolved_data_dto:
            schema = self.resolved_data_dto.create_openapi_schema(
                field_definition=self.field_definition,
                handler_id=self.handler_id,
                schema_creator=self.schema_creator,
            )
        else:
            schema = self.schema_creator.for_field_definition(self.field_definition)

        return RequestBody(required=True, content={media_type: OpenAPIMediaType(schema=schema)})
