# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeGuard

from litestar._openapi.schema_generation.library import MsgspecRoutedPlugin
from litestar.exceptions import MissingDependencyException
from litestar.types import Empty
from litestar.typing import FieldDefinition

try:
    import attr
    import attrs
except ImportError as e:
    raise MissingDependencyException("attrs") from e

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.openapi.spec import Reference, Schema

__all__ = ("AttrsSchemaPlugin", "is_attrs_class")


class AttrsSchemaPlugin(MsgspecRoutedPlugin):
    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return is_attrs_class(value) or is_attrs_class(type(value))

    def _own_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        type_hints = field_definition.get_type_hints(
            include_extras=True, resolve_generics=True, namespace=schema_creator.signature_namespace
        )
        attr_fields = attr.fields_dict(field_definition.type_)
        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(
                field_name for field_name, attribute in attr_fields.items() if attribute.default is attrs.NOTHING
            ),
            property_fields={
                field_name: FieldDefinition.from_kwarg(type_hints[field_name], field_name) for field_name in attr_fields
            },
        )


def is_attrs_class(annotation: Any) -> TypeGuard[type[attrs.AttrsInstance]]:
    """Given a type annotation determine if the annotation is a class that includes an attrs attribute.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is an attrs class.
    """
    return attrs.has(annotation) if attrs is not Empty else False  # type: ignore[comparison-overlap]
