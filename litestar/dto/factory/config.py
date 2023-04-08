"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing import Iterable

    from .field import Purpose
    from .types import FieldDefinition, FieldMappingType


__all__ = ("DTOConfig",)


@dataclass
class DTOConfig:
    """Control the generated DTO."""

    purpose: Purpose | Literal["read", "write"] | None = field(default=None)
    """Configure the DTO for "read" or "write" operations.

    If "write", read-only fields are omitted from data transfer. If "read" or ``None``, read-only fields are included.

    Fields marked "private" are always omitted, irrespective of purpose.
    """
    exclude: set[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO, incompatible with ``include``."""
    include: set[str] = field(default_factory=set)
    """Explicitly include fields on the generated DTO, incompatible with ``exclude``."""
    field_mapping: FieldMappingType = field(default_factory=dict)
    """Mapping of field names, to new name, or tuple of new name, new type."""
    field_definitions: Iterable[FieldDefinition] = field(default_factory=list)
    """Additional fields for data transfer."""
    max_nested_recursion: int = 0
    """The maximum number of times a self-referencing nested field should be followed."""
    max_nested_depth: int = 1
    """The maximum depth of nested items allowed for data transfer."""
