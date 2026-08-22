from types import NoneType, UnionType
from typing import TypeAlias, Union

from typing_extensions import _TypedDictMeta  # type: ignore[attr-defined]

__all__ = (
    "NoneType",
    "TypedDictClass",
    "UnionType",
    "UnionTypes",
)


UnionTypes = {UnionType, Union}
TypedDictClass: TypeAlias = type[_TypedDictMeta]
