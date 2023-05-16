"""DTO domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import AbstractSet

    from litestar.types import AnyCallable

    from .types import RenameStrategy


__all__ = ("DTOConfig",)


@dataclass(frozen=True)
class DTOConfig:
    """Control the generated DTO."""

    exclude: AbstractSet[str] = field(default_factory=set)
    """Explicitly exclude fields from the generated DTO.

    The field names are dot-separated paths to nested fields, e.g. ``"address.street"`` will exclude the ``"street"``
    field from a nested ``"address"`` model.
    """
    rename_fields: dict[str, str] = field(default_factory=dict)
    """Mapping of field names, to new name."""
    rename_strategy: RenameStrategy | None = None
    """Rename all fields using a pre-defined strategy or a custom strategy.

    The pre-defined strategies are: `upper`, `lower`, `camel`, `pascal`.

    A custom strategy is any callable that accepts a string as an argument and
    return a string.

    Fields defined in ``rename_fields`` are ignored."""
    max_nested_depth: int = 1
    """The maximum depth of nested items allowed for data transfer."""
    partial: bool = False
    """Allow transfer of partial data."""
    computed_fields: dict[str, AnyCallable] = field(default_factory=dict)
    """Callables to compute field values.

    The callable's parameters and return type must be fully annotated, and the return type of the callable must match
    the type of the field.
    """
