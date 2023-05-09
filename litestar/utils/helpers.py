from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

__all__ = ("Ref", "get_enum_string_value", "get_fully_qualified_class_name", "get_name", "unwrap_partial")


T = TypeVar("T")

if TYPE_CHECKING:
    from litestar.types import MaybePartial


def get_name(value: Any) -> str:
    """Get the ``__name__`` of an object.

    Args:
        value: An arbitrary object.

    Returns:
        A name string.
    """
    if hasattr(value, "__name__"):
        return cast("str", value.__name__)
    return type(value).__name__


def get_fully_qualified_class_name(value: type[Any]) -> str:
    """Construct the full path name for a type."""
    module = getattr(value, "__module__", "<no module>")
    return f"{module}.{value.__qualname__}"


def get_enum_string_value(value: Enum | str) -> str:
    """Return the string value of a string enum.

    See: https://github.com/litestar-org/litestar/pull/633#issuecomment-1286519267

    Args:
        value: An enum or string.

    Returns:
        A string.
    """
    return value.value if isinstance(value, Enum) else value  # type:ignore


@dataclass
class Ref(Generic[T]):
    """A helper class that encapsulates a value."""

    __slots__ = ("value",)

    value: T
    """The value wrapped by the ref."""


def unwrap_partial(value: MaybePartial[T]) -> T:
    """Unwraps a partial, returning the underlying callable.

    Args:
        value: A partial function.

    Returns:
        Callable
    """
    output: Any = value.func if hasattr(value, "func") else value  # pyright: ignore
    while hasattr(output, "func"):
        output = output.func
    return cast("T", output)
