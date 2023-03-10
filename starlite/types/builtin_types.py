import sys
from typing import TYPE_CHECKING, Type, Union

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from typing_extensions import _TypedDictMeta  # type: ignore


if sys.version_info >= (3, 10):
    from types import NoneType as _NoneType
    from types import UnionType

    NoneType = _NoneType  # type: ignore[valid-type]

    UNION_TYPES = {UnionType, Union}
else:  # pragma: no cover
    UNION_TYPES = {Union}
    NoneType = type(None)

TypedDictClass: TypeAlias = "Type[_TypedDictMeta]"
