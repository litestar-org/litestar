import asyncio
import functools
import sys
from inspect import isclass
from typing import Any, Awaitable, Callable, Type, TypeVar, Union

from typing_extensions import ParamSpec, TypeGuard, get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES = {UnionType, Union}
else:  # pragma: no cover
    UNION_TYPES = {Union}

P = ParamSpec("P")
T = TypeVar("T")


def is_async_callable(value: Callable[P, T]) -> TypeGuard[Callable[P, Awaitable[T]]]:
    """Extends `asyncio.iscoroutinefunction()` to additionally detect async
    `partial` objects and class instances with `async def __call__()` defined.

    Args:
        value: Any

    Returns:
        Bool determining if type of `value` is an awaitable.
    """
    while isinstance(value, functools.partial):
        value = value.func  # type: ignore[unreachable]

    return asyncio.iscoroutinefunction(value) or (callable(value) and asyncio.iscoroutinefunction(value.__call__))  # type: ignore[operator]


def is_class_and_subclass(value: Any, t_type: Type[T]) -> TypeGuard[Type[T]]:
    """Return `True` if `value` is a `class` and is a subtype of `t_type`.

    See https://github.com/starlite-api/starlite/issues/367

    Args:
        value: The value to check if is class and subclass of `t_type`.
        t_type: Type used for `issubclass()` check of `value`

    Returns:
        bool
    """
    origin = get_origin(value)
    if not origin and not isclass(value):
        return False
    try:
        if origin:
            return origin and issubclass(origin, t_type)
        return issubclass(value, t_type)
    except TypeError:
        return False


def is_optional_union(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation infers an optional
    union.

    Args:
        annotation: A type.

    Returns:
        True for a union, False otherwise.
    """
    return get_origin(annotation) in UNION_TYPES and type(None) in get_args(annotation)
