"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from typing import AbstractSet


__all__ = ("DTOConfig",)


@dataclass(frozen=True)
class DTOConfig:
    """Control the generated DTO."""

    exclude: AbstractSet[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO."""
    rename_fields: dict[str, str] = field(default_factory=dict)
    """Mapping of field names, to new name."""
    fields_alias_generator: Callable[[str], str] | None = None
    """A callback for generating aliases of field names. Fields defined in ``rename_fields`` are ignored."""
    max_nested_depth: int = 1
    """The maximum depth of nested items allowed for data transfer."""
