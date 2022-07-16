from typing import Any, Callable

from anyio.to_thread import run_sync

from .helpers import is_async_callable


class LifecycleHook:
    def __init__(self, fn: Callable[..., Any]) -> None:
        self.wrapped = [fn]  # wrap in list to prevent implicit binding
        self.fn_is_async = is_async_callable(fn)

    @property
    def hook(self) -> Callable[..., Any]:
        """The lifecycle hook"""
        return self.wrapped[0]

    async def __call__(self, *args: Any) -> Any:
        if self.fn_is_async:
            return await self.hook(*args)
        return await run_sync(self.hook, *args)
