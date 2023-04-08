from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from typing import Type

    from typing_extensions import TypeAlias, _TypedDictMeta  # type: ignore


if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES = {UnionType, Union}
else:  # pragma: no cover
    UNION_TYPES = {Union}

NoneType: type[None] = type(None)
TypedDictClass: TypeAlias = "Type[_TypedDictMeta]"
