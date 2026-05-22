from __future__ import annotations

from types import NoneType, UnionType
from typing import TYPE_CHECKING, Union

from typing_extensions import _TypedDictMeta  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from typing import TypeAlias

__all__ = (
    "NoneType",
    "TypedDictClass",
    "UnionType",
    "UnionTypes",
)


UnionTypes = {UnionType, Union}
TypedDictClass: TypeAlias = type[_TypedDictMeta]
