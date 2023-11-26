from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn, TypeVar, overload

from litestar.types.empty import Empty

if TYPE_CHECKING:
    from litestar.types.empty import EmptyType

ValueT = TypeVar("ValueT")
DefaultT = TypeVar("DefaultT")


@overload
def raise_if_empty(value: EmptyType) -> NoReturn:
    ...


@overload
def raise_if_empty(value: ValueT | EmptyType) -> ValueT:
    ...


def raise_if_empty(value: ValueT | EmptyType) -> ValueT:
    """Raise an exception if `value` is `Empty`.

    Args:
        value: The value to check.

    Returns:
        The value.

    Raises:
        Exception: When `value` is `Empty`.
    """
    if value is Empty:
        raise ValueError("value cannot be Empty")
    return value


def value_or_default(value: ValueT | EmptyType, default: DefaultT) -> ValueT | DefaultT:
    """Return `value` handling the case where it is empty.

    If `value` is `Empty`, `default` is returned.

    Args:
        value: The value to check.
        default: The default value to return if `value` is `Empty`.

    Returns:
        The value or default value.
    """
    if value is Empty:
        return default
    return value
