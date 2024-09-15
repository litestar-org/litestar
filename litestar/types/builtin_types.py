from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type, Union

from typing_extensions import Never, _TypedDictMeta  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

__all__ = (
    "NoneType",
    "UnionType",
    "UnionTypes",
    "TypedDictClass",
    "EmptyDict",
)

NoneType: type[None] = type(None)

try:
    from types import UnionType  # type: ignore[attr-defined]
except ImportError:
    UnionType: TypeAlias = Union  # type: ignore[no-redef]

UnionTypes = {UnionType, Union}
TypedDictClass: TypeAlias = Type[_TypedDictMeta]
EmptyDict: TypeAlias = Dict[Never, Never]
