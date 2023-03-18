from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Queue, Task, create_task, gather
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Coroutine, DefaultDict, Sequence, cast

from starlite.exceptions import ImproperlyConfiguredException

__all__ = ("BaseEventEmitterBackend", "SimpleEventEmitter")


if TYPE_CHECKING:
    from starlite.events.listener import EventListener


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
    async def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
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

    _queue: Queue | None
    _worker_task: Task | None

    def __init__(self, listeners: Sequence[EventListener]):
        """Create an event emitter instance.

        Args:
            listeners: A list of listeners.
        """
        super().__init__(listeners=listeners)
        self._queue = None
        self._worker_task = None

    async def _worker(self) -> None:
        """Worker that runs in a separate thread and continuously pulls events from asyncio queue.

        Returns:
            None
        """
        while self._queue:
            coroutines = cast("tuple[Coroutine[Any, Any, Any], ...]", await self._queue.get())
            await gather(*coroutines)

    async def on_startup(self) -> None:
        """Hook called on application startup, used to establish connection or perform other async operations.

        Returns:
            None
        """
        try:
            self._queue = Queue()
            self._worker_task = create_task(self._worker())
        except RuntimeError:
            pass

    async def on_shutdown(self) -> None:
        """Hook called on application shutdown, used to perform cleanup.

        Returns:
            None
        """
        if self._worker_task:
            self._worker_task.cancel()

        self._queue = None
        self._worker_task = None

    async def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g 'my_event'.
            *args: args to pass to the listener(s).
            **kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        if self._queue:
            if listeners := self.listeners.get(event_id):
                await self._queue.put(tuple(listener.fn(*args, **kwargs) for listener in listeners))
                return
            raise ImproperlyConfiguredException(f"no event listeners are registered for event ID: {event_id}")
        raise ImproperlyConfiguredException(
            f"{type(self).__name__} can only be used with a running asyncio compatible loop."
        )
