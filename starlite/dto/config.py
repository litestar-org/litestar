"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from .enums import Mark, Purpose
    from .types import FieldDefinitionsType, FieldMappingType


__all__ = ("DTOConfig", "DTOField")


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
    """Configure the DTO for "read" or "write" operations."""
    exclude: set[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO."""
    field_mapping: FieldMappingType = field(default_factory=dict)
    """Mapping of field names, to new name, or tuple of new name, new type."""
    field_definitions: FieldDefinitionsType = field(default_factory=dict)
    """Additional fields for transferred data.

    Key is the name of the new field, and value is a tuple of type and default value pairs.

    Add a new field called "new_field", that is a string, and required:
        {"new_field": (str, ...)}

    Add a new field called "new_field", that is a string, and not-required:
        {"new_field": (str, "default")}

    Add a new field called "new_field", that may be `None`:
        {"new_field": (str | None, None)}
    """
    partial: bool = field(default=False)
    """DTO should allow incomplete object representation."""
    private_fields: set[str] = field(default_factory=set)
    """Names of fields that should never be included in data transfer, either in or out."""
    read_only_fields: set[str] = field(default_factory=set)
    """Names of fields that should never be parsed from input data."""
    backend_kwargs: Mapping[str, Any] = field(default_factory=dict)
    """Kwargs passed through to the DTO backend instance."""
