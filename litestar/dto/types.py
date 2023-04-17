from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

    from typing_extensions import TypeAlias

__all__ = ("ForType",)

ForType: TypeAlias = "Literal['data', 'return']"
"""Type for parameters that express the purpose of DTO application."""
