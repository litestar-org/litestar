from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.dto.factory.types import FieldDefinition

if TYPE_CHECKING:
    from typing import Any, Mapping

    from typing_extensions import TypeAlias

    from litestar.utils.signature import ParsedType


@dataclass
class TransferModel:
    """Type for representing fields and model type of nested model type."""

    model: type[Any]
    field_definitions: FieldDefinitionsType


@dataclass
class TransferType:
    """Type for representing model types for data transfer."""

    __slots__ = ("parsed_type",)

    parsed_type: ParsedType


@dataclass
class SimpleType(TransferType):
    """Represents indivisible, non-composite types."""

    __slots__ = ("transfer_model",)

    transfer_model: TransferModel | None
    """If the type is a 'nested' type, this is the model generated for transfer to/from it."""


@dataclass
class CompositeType(TransferType):
    """A type that is made up of other types."""

    __slots__ = ("has_nested",)

    has_nested: bool
    """Whether the type represents nested model types within itself."""


@dataclass
class UnionType(CompositeType):
    """Type for representing union types for data transfer."""

    inner_types: tuple[TransferType, ...]


@dataclass
class CollectionType(CompositeType):
    """Type for representing collection types for data transfer."""

    inner_type: TransferType


@dataclass
class TupleType(CompositeType):
    """Type for representing tuples for data transfer."""

    inner_types: tuple[TransferType, ...]


@dataclass
class MappingType(CompositeType):
    """Type for representing mappings for data transfer."""

    key_type: TransferType
    value_type: TransferType


@dataclass(frozen=True)
class TransferFieldDefinition(FieldDefinition):
    transfer_type: TransferType
    """Type of the field for transfer."""
    serialization_name: str | None = field(default=None)
    """Name of the field as it should feature on the transfer model."""


"""For typing where any field definition is allowed."""
FieldDefinitionsType: TypeAlias = "Mapping[str, TransferFieldDefinition]"
"""Generic representation of names and types."""
