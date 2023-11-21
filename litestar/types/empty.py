from __future__ import annotations

__all__ = ("_EMPTY", "_LiteralEmpty", "Empty", "EmptyType")

from enum import Enum
from typing import TYPE_CHECKING, Literal, Type, final

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


@final
class Empty:
    """A sentinel class used as placeholder."""


EmptyType: TypeAlias = Type[Empty]


class _EmptyEnum(Enum):
    """A sentinel enum used as placeholder."""

    EMPTY = 0


_LiteralEmpty = Literal[_EmptyEnum.EMPTY]
_EMPTY = _EmptyEnum.EMPTY
