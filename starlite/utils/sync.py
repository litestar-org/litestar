from functools import partial
from typing import TYPE_CHECKING, Any, Dict

from anyio.to_thread import run_sync

from starlite.utils.predicates import is_async_callable

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable


class AsyncCallable:
    __slots__ = ("args", "kwargs", "fn")

    def __init__(self, fn: "AnyCallable"):
        """Utility class that wraps a callable and ensures it can be called as
        an async function.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """
        if is_async_callable(fn):
            self.fn = fn
        else:
            self.fn = partial(run_sync, fn)

    async def __call__(self, *args: Any, **kwargs: Dict[str, Any]) -> Any:
        return await self.fn(*args, **kwargs)
