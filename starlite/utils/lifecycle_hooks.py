from functools import partial
from typing import Any, Callable

from anyio.to_thread import run_sync

from .helpers import is_async_callable


class LifecycleHook:
    """
    Container for assignment of lifecycle hook handlers to instances.

    A callable assigned to a class is implicitly converted to a bound method on an instance:

        >>> def a_callable(): ...
        ...
        >>> class C:
        ...   callable = a_callable
        ...
        >>> C().callable()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        TypeError: a_callable() takes 0 positional arguments but 1 was given

    `LifecycleHook` supports the pattern of storing handlers as attributes of the application layers, and caching
    resolved handlers on `HTTPRouteHandler` instances.

    Additionally, it pre-computes whether the handler function is async, simplifying calling the handler during the
    request/response cycle.
    """

    def __init__(self, handler: Callable[..., Any]) -> None:
        if is_async_callable(handler):
            self.wrapped = [handler]  # wrap in list to prevent implicit binding
        else:
            self.wrapped = [partial(run_sync, handler)]

    async def __call__(self, *args: Any) -> Any:
        return await self.wrapped[0](*args)
