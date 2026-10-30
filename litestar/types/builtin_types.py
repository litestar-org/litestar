from types import NoneType, UnionType
from typing import Union

from typing_extensions import TypeAliasType, _TypedDictMeta  # type: ignore[attr-defined]

__all__ = (
    "NoneType",
    "TypedDictClass",
    "UnionType",
    "UnionTypes",
)


UnionTypes = {UnionType, Union}
TypedDictClass = TypeAliasType("TypedDictClass", type[_TypedDictMeta])
