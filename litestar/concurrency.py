import asyncio
import contextvars
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


__all__ = (
    "get_asyncio_executor",
    "set_asyncio_executor",
    "sync_to_thread",
)


class _State:
    EXECUTOR: ThreadPoolExecutor | None = None


async def sync_to_thread(fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Run the synchronous callable ``fn`` asynchronously in a worker thread.

    Uses :meth:`asyncio.loop.run_in_executor` to run the callable. No executor is
    specified by default so the current loop's executor is used. A specific executor can be
    set using :func:`~litestar.concurrency.set_asyncio_executor`. This does not affect the
    loop's default executor.
    """
    ctx = contextvars.copy_context()
    bound_fn = partial(ctx.run, fn, *args, **kwargs)
    return await asyncio.get_running_loop().run_in_executor(get_asyncio_executor(), bound_fn)


def set_asyncio_executor(executor: ThreadPoolExecutor | None) -> None:
    """Set the executor in which synchronous callables will be run within an asyncio
    context
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Cannot set executor from running loop")

    _State.EXECUTOR = executor


def get_asyncio_executor() -> ThreadPoolExecutor | None:
    """Get the executor in which synchronous callables will be run within an asyncio
    context
    """
    return _State.EXECUTOR
