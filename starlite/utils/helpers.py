from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Optional, TypeVar, Union, cast

T = TypeVar("T")


def get_name(value: Any) -> str:
    """Helper to get the '__name__' dunder of a value.

    Args:
        value: An arbitrary value.

    Returns:
        A name string.
    """

    if hasattr(value, "__name__"):
        return cast("str", value.__name__)
    return type(value).__name__


def get_enum_string_value(value: Union[Enum, str]) -> str:
    """A helper function to return the string value of a string enum.

    See: https://github.com/starlite-api/starlite/pull/633#issuecomment-1286519267

    Args:
        value: An enum or string.

    Returns:
        A string.
    """
    return cast("str", value.value) if isinstance(value, Enum) else value


@dataclass
class Ref(Generic[T]):
    """A helper class that encapsulates a value."""

    __slots__ = ("value",)

    value: Optional[T]
    """The value wrapped by the ref."""
