"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Iterable

    from .enums import Mark, Purpose
    from .types import FieldDefinition, FieldMappingType


__all__ = (
    "DTO_FIELD_META_KEY",
    "DTOConfig",
    "DTOField",
)


DTO_FIELD_META_KEY = "__dto__"


@dataclass
class DTOField:
    """For configuring DTO behavior on model fields."""

    mark: Mark | None = None
    """Mark the field as read-only, or private."""
    field_type: Any | None = None
    """Override the field type for this attribute."""


@dataclass
class DTOConfig:
    """Control the generated DTO."""

    purpose: Purpose | None = field(default=None)
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
    partial: bool = field(default=False)
    """DTO should allow incomplete object representation."""
    max_nested_recursion: int = 0
    """The maximum number of times a self-referencing nested field should be followed."""
    max_nested_depth: int = 1
    """The maximum depth of nested items allowed for data transfer."""
    backend_kwargs: Mapping[str, Any] = field(default_factory=dict)
    """Kwargs passed through to the DTO backend instance."""
