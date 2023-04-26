"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import AbstractSet


__all__ = ("DTOConfig",)


@dataclass(frozen=True)
class DTOConfig:
    """Control the generated DTO."""

    exclude: AbstractSet[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO, incompatible with ``include``."""
    rename_fields: dict[str, str] = field(default_factory=dict)
    """Mapping of field names, to new name."""
    max_nested_depth: int = 1
    """The maximum depth of nested items allowed for data transfer."""
