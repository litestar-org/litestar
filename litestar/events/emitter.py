from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import CancelledError, Queue, Task, create_task
from collections import defaultdict
from contextlib import suppress
from typing import TYPE_CHECKING, Any, DefaultDict, Sequence

import sniffio

from litestar.exceptions import ImproperlyConfiguredException

__all__ = ("BaseEventEmitterBackend", "SimpleEventEmitter")


if TYPE_CHECKING:
    from litestar.events.listener import EventListener


class BaseEventEmitterBackend(ABC):
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

    @abstractmethod
    async def on_startup(self) -> None:  # pragma: no cover
        """Hook called on application startup, used to establish connection or perform other async operations.

        Returns:
            None
        """
        raise NotImplementedError("not implemented")

    @abstractmethod
    async def on_shutdown(self) -> None:  # pragma: no cover
        """Hook called on application shutdown, used to perform cleanup.

        Returns:
            None
        """
        raise NotImplementedError("not implemented")


class SimpleEventEmitter(BaseEventEmitterBackend):
    """Event emitter the works only in the current process"""

    __slots__ = ("_queue", "_worker_task")

    _worker_task: Task | None

    def __init__(self, listeners: Sequence[EventListener]):
        """Create an event emitter instance.

        Args:
            listeners: A list of listeners.
        """
        super().__init__(listeners=listeners)
        self._queue: Queue | None = None
        self._worker_task = None

    async def _worker(self) -> None:
        """Worker that runs in a separate task and continuously pulls events from asyncio queue.

        Returns:
            None
        """
        while self._queue:
            fn, args, kwargs = await self._queue.get()
            await fn(*args, **kwargs)
            self._queue.task_done()

    async def on_startup(self) -> None:
        """Hook called on application startup, used to establish connection or perform other async operations.

        Returns:
            None
        """
        if sniffio.current_async_library() != "asyncio":
            return

        self._queue = Queue()
        self._worker_task = create_task(self._worker())

    async def on_shutdown(self) -> None:
        """Hook called on application shutdown, used to perform cleanup.

        Returns:
            None
        """

        if self._queue:
            await self._queue.join()

        if self._worker_task:
            self._worker_task.cancel()
            with suppress(CancelledError):
                await self._worker_task

        self._worker_task = None
        self._queue = None

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g 'my_event'.
            *args: args to pass to the listener(s).
            **kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        if not (self._worker_task and self._queue):
            if sniffio.current_async_library() != "asyncio":
                raise ImproperlyConfiguredException("{type(self).__name__} only supports 'asyncio' based event loops")

            raise ImproperlyConfiguredException("Worker not running")

        if listeners := self.listeners.get(event_id):
            for listener in listeners:
                self._queue.put_nowait((listener.fn, args, kwargs))
            return
        raise ImproperlyConfiguredException(f"no event listeners are registered for event ID: {event_id}")
