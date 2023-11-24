from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn, TypeVar, overload

from litestar.types.empty import Empty

if TYPE_CHECKING:
    from litestar.types.empty import EmptyType

ValueT = TypeVar("ValueT")
DefaultT = TypeVar("DefaultT")


@overload
def not_empty(value: EmptyType) -> NoReturn:
    ...


@overload
def not_empty(value: EmptyType, default: EmptyType) -> NoReturn:
    ...


@overload
def not_empty(value: ValueT | EmptyType) -> ValueT:
    ...


@overload
def not_empty(value: ValueT | EmptyType, default: EmptyType) -> ValueT:
    ...


@overload
def not_empty(value: ValueT | EmptyType, default: DefaultT) -> ValueT | DefaultT:
    ...


def not_empty(value: ValueT | EmptyType, default: DefaultT | EmptyType = Empty) -> ValueT | DefaultT:
    """Return `value` handling the case where it is empty.

    If default is provided, it is returned when `value` is `Empty`.

    If default is not provided, raises a `ValueError` when `value` is `Empty`.

    Args:
        value: The value to check.
        default: The default value to return if `value` is `Empty`.

    Returns:
        The value or default value.

    Raises:
        ValueError: When `value` is `Empty` and `default` is not provided.
    """
    if value is Empty:
        if default is Empty:
            raise ValueError("value cannot be Empty")
        return default
    return value
