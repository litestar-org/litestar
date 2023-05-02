from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.dto.factory.types import FieldDefinition

if TYPE_CHECKING:
    from typing import Any, Mapping

    from typing_extensions import TypeAlias


@dataclass(frozen=True)
class TransferFieldDefinition(FieldDefinition):
    serialization_name: str | None = field(default=None)
    """Name of the field as it should feature on the transfer model."""


@dataclass
class NestedFieldDefinition:
    """For representing nested model."""

    field_definition: TransferFieldDefinition
    nested_type: Any
    nested_field_definitions: FieldDefinitionsType = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Name of the field."""
        return self.field_definition.name

    @property
    def serialization_name(self) -> str | None:
        """Serialization name of the field."""
        return self.field_definition.serialization_name

    def make_field_type(self, inner_type: type) -> Any:
        if self.field_definition.parsed_type.is_collection:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type]
        if self.field_definition.parsed_type.is_optional:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type, None]
        return inner_type


FieldDefinitionsType: TypeAlias = "Mapping[str, TransferFieldDefinition | NestedFieldDefinition]"
"""Generic representation of names and types."""
