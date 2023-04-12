from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.types.empty import Empty
from litestar.utils.dataclass import simple_asdict
from litestar.utils.signature import ParsedParameter

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Callable

    from typing_extensions import TypeAlias

    from litestar.types import EmptyType

    from .field import DTOField

__all__ = (
    "FieldDefinition",
    "FieldDefinitionsType",
    "FieldMappingType",
    "NestedFieldDefinition",
)


@dataclass(frozen=True)
class FieldDefinition(ParsedParameter):
    """A model field representation for purposes of generating a DTO backend model type."""

    default_factory: Callable[[], Any] | EmptyType = field(default=Empty)
    """Default factory of the field."""
    dto_field: DTOField | None = field(default=None)
    """DTO field configuration."""

    def copy_with(self, **kwargs: Any) -> FieldDefinition:
        """Copy the field definition with the given keyword arguments.

        Args:
            **kwargs: Keyword arguments to update the field definition with.

        Returns:
            Updated field definition.
        """
        return FieldDefinition(**{**simple_asdict(self, convert_nested=False), **kwargs})


@dataclass
class NestedFieldDefinition:
    """For representing nested model."""

    field_definition: FieldDefinition
    nested_type: Any
    nested_field_definitions: FieldDefinitionsType = field(default_factory=dict)

    def is_recursive(self, model_type: type) -> bool:
        """Indicate if ``nested_type`` is a subtype of ``model_type``.

        Args:
            model_type: type that is having a DTO generated.

        Returns:
            Indication if the nested field is recursive.
        """
        return any(
            inner_type.is_subclass_of(model_type) for inner_type in self.field_definition.parsed_type.inner_types
        )

    def make_field_type(self, inner_type: type) -> Any:
        if self.field_definition.parsed_type.is_collection:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type]
        if self.field_definition.parsed_type.is_optional:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type, None]
        return inner_type


FieldDefinitionsType: TypeAlias = "Mapping[str, FieldDefinition | NestedFieldDefinition]"
"""Generic representation of names and types."""

FieldMappingType: TypeAlias = "Mapping[str, str | FieldDefinition]"
"""Type of the field mappings configuration property."""
