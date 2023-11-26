from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from litestar.types.empty import Empty

if TYPE_CHECKING:
    from litestar.types.empty import EmptyType

ValueT = TypeVar("ValueT")
DefaultT = TypeVar("DefaultT")


def value_or_default(value: ValueT | EmptyType, default: DefaultT) -> ValueT | DefaultT:
    """Return `value` handling the case where it is empty.

    If `value` is `Empty`, `default` is returned.

    Args:
        value: The value to check.
        default: The default value to return if `value` is `Empty`.

    Returns:
        The value or default value.
    """
    return default if value is Empty else value
