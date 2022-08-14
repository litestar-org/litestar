import asyncio
import functools
from inspect import isclass
from typing import Any, Callable


def is_async_callable(value: Callable) -> bool:
    """
    Extends `asyncio.iscoroutinefunction()` to additionally detect async `partial` objects and
    class instances with `async def __call__()` defined.

    Args:
        value: Any

    Returns:
        bool
    """
    while isinstance(value, functools.partial):
        value = value.func

    return asyncio.iscoroutinefunction(value) or asyncio.iscoroutinefunction(value.__call__)  # type: ignore[operator]


def is_class_and_subclass(value: Any, t_type: Any) -> bool:
    """
    Return `True` if `value` is a `class` and is a subtype of `t_type`.

    See https://github.com/starlite-api/starlite/issues/367

    Args:
        value: The value to check if is class and subclass of `t_type`.
        t_type: Type used for `issubclass()` check of `value`

    Returns:
        bool
    """
    if not isclass(value):
        return False
    try:
        return issubclass(value, t_type)
    except TypeError:
        return False
