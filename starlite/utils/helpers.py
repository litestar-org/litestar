from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from starlite.exceptions import MissingDependencyException

__all__ = ("Ref", "get_enum_string_value", "get_name", "unwrap_partial", "raise_if_not_installed")


T = TypeVar("T")

if TYPE_CHECKING:
    from starlite.types import MaybePartial


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


def get_enum_string_value(value: Enum | str) -> str:
    """Return the string value of a string enum.

    See: https://github.com/starlite-api/starlite/pull/633#issuecomment-1286519267

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


def raise_if_not_installed(package_name: str, install_package: str | None = None) -> None:
    """Raise :exc:`MissingDependencyException` if ``package_name`` is not importable"""
    try:
        __import__(package_name)
    except ImportError as e:
        raise MissingDependencyException(package_name, install_package=install_package) from e
