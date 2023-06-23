from __future__ import annotations

from typing import TYPE_CHECKING, Type, Union

from typing_extensions import _TypedDictMeta  # type: ignore

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

__all__ = (
    "NoneType",
    "UnionType",
    "UnionTypes",
    "TypedDictClass",
)

try:
    from types import NoneType, UnionType  # pyright: ignore
except ImportError:
    NoneType: TypeAlias = type(None)  # type: ignore
    UnionType: TypeAlias = Union  # type: ignore

UnionTypes = {UnionType, Union}
TypedDictClass: TypeAlias = Type[_TypedDictMeta]
