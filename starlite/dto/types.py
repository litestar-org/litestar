from __future__ import annotations

from typing import Any, TypeVar

__all__ = ("DataT", "StarliteEncodableType")

DataT = TypeVar("DataT")
"""Type var representing data held by a DTO instance."""

StarliteEncodableType = Any
"""Types able to be encoded by Starlite."""
