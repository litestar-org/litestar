from functools import partial
from typing import Awaitable, Callable, Generic, TypeVar

from anyio.to_thread import run_sync
from typing_extensions import ParamSpec

from starlite.utils.predicates import is_async_callable

P = ParamSpec("P")
T = TypeVar("T")


class AsyncCallable(Generic[P, T]):
    __slots__ = ("args", "kwargs", "fn")

    def __init__(self, fn: Callable[P, T]):
        """Utility class that wraps a callable and ensures it can be called as
        an async function.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """
        self.fn: Callable[P, Awaitable[T]]
        if is_async_callable(fn):
            self.fn = fn
        else:
            self.fn = partial(run_sync, fn)  # type:ignore[assignment]

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self.fn(*args, **kwargs)
