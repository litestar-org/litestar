from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from typing_extensions import TypeAlias

__all__ = (
    "DataT",
    "FieldDefinitionsType",
    "FieldMappingType",
    "StarliteEncodableType",
)

DataT = TypeVar("DataT")
"""Type var representing data held by a DTO instance."""

FieldDefinitionsType: TypeAlias = "Mapping[str, tuple[type, Any]]"
"""Generic representation of names and types."""

FieldMappingType: TypeAlias = "Mapping[str, tuple[str, type]]"
"""Type of the field mappings configuration property."""

StarliteEncodableType: TypeAlias = "Any"
"""Types able to be encoded by Starlite."""
