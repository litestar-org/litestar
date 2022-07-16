import asyncio
import functools
from inspect import ismethod
from typing import Any, Callable


def is_async_callable(obj: Any) -> bool:
    """
    Extends `asyncio.iscoroutinefunction()` to additionally detect async `partial` objects and
    class instances with `async def __call__()` defined.

    Parameters
    ----------
    obj : Any

    Returns
    -------
    bool
    """
    while isinstance(obj, functools.partial):
        obj = obj.func

    return asyncio.iscoroutinefunction(obj) or (callable(obj) and asyncio.iscoroutinefunction(obj.__call__))


def ensure_unbound(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    If `fn` is a method, returns its `__func__` attribute.

    Args:
        fn (Callable[..., Any]): Any callable

    Returns:
        Callable[..., Any]: A callable that is not a bound method.
    """
    if ismethod(fn):
        return fn.__func__
    return fn
