from __future__ import annotations

from enum import Enum

__all__ = ("Mark", "Purpose")


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
