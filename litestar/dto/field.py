"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

__all__ = (
    "DTO_FIELD_META_KEY",
    "DTOField",
    "Mark",
    "dto_field",
)

DTO_FIELD_META_KEY = "__dto__"


class Mark(str, Enum):
    """For marking field definitions on domain models."""

    READ_ONLY = "read-only"
    """To mark a field that can be read, but not updated by clients."""
    WRITE_ONLY = "write-only"
    """To mark a field that can be written to, but not read by clients."""
    PRIVATE = "private"
    """To mark a field that can neither be read or updated by clients."""


@dataclass
class DTOField:
    """For configuring DTO behavior on model fields."""

    mark: Mark | Literal["read-only", "write-only", "private"] | None = None
    """Mark the field as read-only, or private."""


def dto_field(mark: Literal["read-only", "write-only", "private"] | Mark) -> dict[str, DTOField]:
    """Create a field metadata mapping.

    Args:
        mark: A DTO mark for the field, e.g., "read-only".

    Returns:
        A dict for setting as field metadata, such as the dataclass "metadata" field key, or the SQLAlchemy "info"
        field.

        Marking a field automates its inclusion/exclusion from DTO field definitions, depending on the DTO's purpose.
    """
    return {DTO_FIELD_META_KEY: DTOField(mark=Mark(mark))}
