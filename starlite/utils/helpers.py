import asyncio
import functools
from typing import Any


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
