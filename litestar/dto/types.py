from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal, TypeAlias

__all__ = ("RenameStrategy",)

RenameStrategy: TypeAlias = 'Literal["lower", "upper", "camel", "pascal", "kebab"] | Callable[[str], str]'
"""A pre-defined strategy or a custom callback for converting DTO field names."""
