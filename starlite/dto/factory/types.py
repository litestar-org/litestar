from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from starlite.types import Empty

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Callable

    from typing_extensions import TypeAlias

    from starlite.types import EmptyType

    from .config import DTOField

__all__ = (
    "FieldDefinition",
    "FieldDefinitionsType",
    "FieldMappingType",
    "NestedFieldDefinition",
)


@dataclass
class FieldDefinition:
    """A model field representation for purposes of generating a DTO backend model type."""

    field_name: str
    """Name of the field."""
    field_type: type
    """Type of the field."""
    default: Any = field(default=Empty)
    """Default value of the field."""
    default_factory: Callable[[], Any] | EmptyType = field(default=Empty)
    """Default factory of the field."""
    dto_field: DTOField | None = field(default=None)
    """DTO field configuration."""


@dataclass
class NestedFieldDefinition:
    """For representing nested model."""

    field_definition: FieldDefinition
    origin: Any | None
    args: tuple[Any, ...]
    nested_type: Any
    nested_field_definitions: FieldDefinitionsType = field(default_factory=dict)

    def is_recursive(self, model_type: type) -> bool:
        """Indicate if ``nested_type`` is a subtype of ``model_type``.

        Args:
            model_type: type that is having a DTO generated.

        Returns:
            Indication if the nested field is recursive.
        """
        return issubclass(self.nested_type, model_type)

    def make_field_type(self, inner_type: type) -> Any:
        if self.origin:
            if hasattr(self.field_definition.field_type, "copy_with"):
                return self.field_definition.field_type.copy_with(inner_type)  # pyright: ignore
            return self.origin[inner_type]  # pragma: no cover
        return inner_type


FieldDefinitionsType: TypeAlias = "Mapping[str, FieldDefinition | NestedFieldDefinition]"
"""Generic representation of names and types."""

FieldMappingType: TypeAlias = "Mapping[str, str | FieldDefinition]"
"""Type of the field mappings configuration property."""
