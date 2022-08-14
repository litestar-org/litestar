import asyncio
import functools
import inspect
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


def is_class_and_subclass(item: Any, type_: Any) -> bool:
    """
    Return `True` if `test` is a `class` and is a subtype of `type_`.

    See https://github.com/starlite-api/starlite/issues/367

    Args:
        item (Any): The item to test if is class and subclass of `type_`.
        type_ (Any): Type used for `issubclass()` test of `item`

    Returns:
    bool
    """
    item_is_class = inspect.isclass(item)
    if not item_is_class:
        return False
    try:
        return issubclass(item, type_)
    except TypeError:
        return False
