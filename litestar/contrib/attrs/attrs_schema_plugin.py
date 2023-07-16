from __future__ import annotations

from typing import TYPE_CHECKING, Any

from typing_extensions import get_type_hints

from litestar._openapi.schema_generation.schema import _get_type_schema_name
from litestar.exceptions import MissingDependencyException
from litestar.openapi.spec import OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPluginProtocol
from litestar.typing import FieldDefinition
from litestar.utils import is_attrs_class, is_optional_union

try:
    import attr
    import attrs
except ImportError as e:
    raise MissingDependencyException("attrs") from e

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.dto.types import ForType


class AttrsSchemaPlugin(OpenAPISchemaPluginProtocol):
    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return is_attrs_class(value) or is_attrs_class(type(value))

    def to_openapi_schema(self, annotation: Any, schema_creator: SchemaCreator, dto_for: ForType | None) -> Schema:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            annotation: A type annotation.
            schema_creator: An instance of the schema creator class
            dto_for: The type of the DTO if any.

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """

        annotation_hints = get_type_hints(annotation, include_extras=True)
        return Schema(
            required=sorted(
                [
                    field_name
                    for field_name, attribute in attr.fields_dict(annotation).items()
                    if attribute.default is attrs.NOTHING and not is_optional_union(annotation_hints[field_name])
                ]
            ),
            properties={
                k: schema_creator.for_field_definition(FieldDefinition.from_kwarg(v, k))
                for k, v in annotation_hints.items()
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(annotation, dto_for),
        )
