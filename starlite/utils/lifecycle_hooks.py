from typing import Any, Callable

from anyio.to_thread import run_sync

from .helpers import is_async_callable


class LifecycleHook:
    def __init__(self, handler: Callable[..., Any]) -> None:
        self.wrapped = [handler]  # wrap in list to prevent implicit binding
        self.is_async_handler = is_async_callable(handler)

    async def __call__(self, *args: Any) -> Any:
        if self.is_async_handler:
            return await self.wrapped[0](*args)
        return await run_sync(self.wrapped[0], *args)
