from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

__all__ = ("RenameStrategy",)

RenameStrategy: TypeAlias = 'Literal["lower", "upper", "camel", "pascal"] | Callable[[str], str]'
"""A pre-defined strategy or a custom callback for converting DTO field names."""
