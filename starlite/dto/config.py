"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

__all__ = ("DTOConfig", "DTOField", "Mark", "Purpose")


class Mark(str, Enum):
    """For marking field definitions on domain models."""

    READ_ONLY = "read-only"
    """To mark a field that can be read, but not updated by clients."""
    PRIVATE = "private"
    """To mark a field that can neither be read or updated by clients."""


class Purpose(str, Enum):
    """For identifying the purpose of a DTO.

    The factory will exclude fields marked as private or read-only on the domain model depending
    on the purpose of the DTO.
    """

    READ = "read"
    """To mark a DTO that is to be used to serialize data returned to
    clients."""
    WRITE = "write"
    """To mark a DTO that is to deserialize and validate data provided by
    clients."""


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

    purpose: Purpose = field(default=Purpose.READ)
    """Configure the DTO for "read" or "write" operations."""
    exclude: set[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO."""
    field_mapping: dict[str, str | tuple[str, type]] = field(default_factory=dict)
    """Mapping of field names, to new name, or tuple of new name, new type."""
    field_definitions: dict[str, tuple[type, Any]] = field(default_factory=dict)
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
