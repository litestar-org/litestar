from typing import Any, Callable

from anyio.to_thread import run_sync

from .helpers import is_async_callable


class LifecycleHook:
    def __init__(self, handler: Callable[..., Any]) -> None:
        self.wrapped = [handler]  # wrap in list to prevent implicit binding
        self.is_async_handler = is_async_callable(handler)

    @property
    def hook(self) -> Callable[..., Any]:
        """The lifecycle hook"""
        return self.wrapped[0]

    async def __call__(self, *args: Any) -> Any:
        if self.is_async_handler:
            return await self.hook(*args)
        return await run_sync(self.hook, *args)
