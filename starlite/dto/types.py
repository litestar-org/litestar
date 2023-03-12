from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar

from starlite.types import Empty

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from typing import Any, Callable

    from starlite.types import EmptyType
    from typing_extensions import TypeAlias

__all__ = (
    "DataT",
    "FieldDefinition",
    "FieldDefinitionsType",
    "FieldMappingType",
    "NestedFieldDefinition",
    "StarliteEncodableType",
)


@dataclass
class FieldDefinition:
    field_type: type
    default: Any = field(default=Empty)
    default_factory: Callable[[], Any] | EmptyType = field(default=Empty)


@dataclass
class NestedFieldDefinition:
    """For representing nested model."""

    field_definition: FieldDefinition
    origin: type
    args: tuple[Any, ...]
    nested_type: Any
    nested_field_definitions: dict[str, FieldDefinition] = field(default_factory=dict)
    collection_type: type[Collection] | EmptyType = field(default=Empty)

    def is_recursive(self, model_type: type) -> bool:
        """Indicate if :attribute:`nested_type` is a subtype of ``model_type``.

        Args:
            model_type: type that is having a DTO generated.

        Returns:
            Indication if the nested field is recursive.
        """
        return issubclass(self.nested_type, model_type)

    def make_collection_type(self, inner_type: type) -> Any:
        if self.origin:
            if hasattr(self.field_definition.field_type, "copy_with"):
                return self.field_definition.field_type.copy_with(inner_type)
            return self.origin[inner_type]


DataT = TypeVar("DataT")
"""Type var representing data held by a DTO instance."""

FieldDefinitionsType: TypeAlias = "Mapping[str, FieldDefinition | NestedFieldDefinition]"
"""Generic representation of names and types."""

FieldMappingType: TypeAlias = "Mapping[str, tuple[str, type]]"
"""Type of the field mappings configuration property."""

StarliteEncodableType: TypeAlias = "Any"
"""Types able to be encoded by Starlite."""
