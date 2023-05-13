from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Queue
from collections import defaultdict
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import TYPE_CHECKING, Any, DefaultDict, Sequence

import anyio
import sniffio

from litestar.exceptions import ImproperlyConfiguredException

__all__ = ("BaseEventEmitterBackend", "SimpleEventEmitter")


if TYPE_CHECKING:
    from litestar.events.listener import EventListener


class BaseEventEmitterBackend(AbstractAsyncContextManager, ABC):
    """Abstract class used to define event emitter backends."""

    __slots__ = ("listeners",)

    listeners: DefaultDict[str, set[EventListener]]

    def __init__(self, listeners: Sequence[EventListener]):
        """Create an event emitter instance.

        Args:
            listeners: A list of listeners.
        """
        self.listeners = defaultdict(set)
        for listener in listeners:
            for event_id in listener.event_ids:
                self.listeners[event_id].add(listener)

    @abstractmethod
    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g 'my_event'.
            *args: args to pass to the listener(s).
            **kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        raise NotImplementedError("not implemented")


class SimpleEventEmitter(BaseEventEmitterBackend):
    """Event emitter the works only in the current process"""

    __slots__ = ("_queue", "_exit_stack")

    def __init__(self, listeners: Sequence[EventListener]):
        """Create an event emitter instance.

        Args:
            listeners: A list of listeners.
        """
        super().__init__(listeners=listeners)
        self._queue: Queue | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def _worker(self) -> None:
        """Worker that runs in a separate task and continuously pulls events from asyncio queue.

        Returns:
            None
        """
        while self._queue:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            fn, args, kwargs = item
            await fn(*args, **kwargs)
            self._queue.task_done()

    async def __aenter__(self) -> SimpleEventEmitter:
        if sniffio.current_async_library() != "asyncio":
            return self

        self._queue = Queue()
        self._exit_stack = AsyncExitStack()
        task_group = anyio.create_task_group()
        await self._exit_stack.enter_async_context(task_group)
        task_group.start_soon(self._worker)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._queue:
            self._queue.put_nowait(None)
            self._queue = None

        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g 'my_event'.
            *args: args to pass to the listener(s).
            **kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        if not self._queue:
            if sniffio.current_async_library() != "asyncio":
                raise ImproperlyConfiguredException(f"{type(self).__name__} only supports 'asyncio' based event loops")

            raise ImproperlyConfiguredException("Worker not running")

        if listeners := self.listeners.get(event_id):
            for listener in listeners:
                self._queue.put_nowait((listener.fn, args, kwargs))
            return
        raise ImproperlyConfiguredException(f"no event listeners are registered for event ID: {event_id}")
