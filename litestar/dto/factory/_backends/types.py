from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.dto.factory.types import FieldDefinition

if TYPE_CHECKING:
    from typing import Any, Mapping

    from typing_extensions import TypeAlias

    from litestar.utils.signature import ParsedType


@dataclass(frozen=True)
class TransferFieldDefinition(FieldDefinition):
    serialization_name: str | None = field(default=None)
    """Name of the field as it should feature on the transfer model."""


@dataclass(frozen=True)
class NestedBase:
    field_definition: TransferFieldDefinition

    @property
    def name(self) -> str:
        """Name of the field."""
        return self.field_definition.name

    @property
    def parsed_type(self) -> ParsedType:
        """Parsed type of the field."""
        return self.field_definition.parsed_type

    @property
    def serialization_name(self) -> str | None:
        """Serialization name of the field."""
        return self.field_definition.serialization_name

    @property
    def unique_name(self) -> str:
        """Unique name of the field."""
        return self.field_definition.unique_name

    def make_field_type(self, inner_type: type) -> Any:
        if self.field_definition.parsed_type.is_collection:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type]
        if self.field_definition.parsed_type.is_optional:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type, None]
        return inner_type


@dataclass(frozen=True)
class NestedFieldDefinition(NestedBase):
    """For representing nested model."""

    nested_type: type[Any]
    transfer_model: type[Any]
    nested_field_definitions: FieldDefinitionsType = field(default_factory=dict)


@dataclass(frozen=True)
class NestedMultiType(NestedBase):
    """A nested type that may have one or more nested types, e.g., tuples and unions."""

    nested_types: tuple[Any, ...]
    transfer_models: tuple[Any, ...]
    nested_field_definitions: tuple[FieldDefinitionsType, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NestedTuple(NestedMultiType):
    """A tuple where at least one of the inner types is a nested model."""


@dataclass(frozen=True)
class NestedUnion(NestedMultiType):
    """A tuple where at least one of the inner types is a nested model."""


AnyFieldDefinition: TypeAlias = "TransferFieldDefinition | NestedFieldDefinition | NestedUnion"
"""For typing where any field definition is allowed."""
FieldDefinitionsType: TypeAlias = "Mapping[str, AnyFieldDefinition]"
"""Generic representation of names and types."""
