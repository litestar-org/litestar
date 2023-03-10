from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, Any, DefaultDict

from anyio import create_task_group

from starlite.exceptions import ImproperlyConfiguredException

__all__ = ("BaseEventEmitterBackend", "SimpleEventEmitter")


if TYPE_CHECKING:
    from starlite.events.listener import EventListener
    from starlite.utils import AsyncCallable


class BaseEventEmitterBackend(ABC):
    """Abstract class used to define event emitter backends."""

    __slots__ = ("listeners",)

    listeners: DefaultDict[str, list[AsyncCallable[Any, Any]]]

    def __init__(self, listeners: list[EventListener]):
        """Create an event emitter instance.

        Args:
            listeners: A list of listeners.
        """
        self.listeners = defaultdict(list)
        for listener in listeners:
            for event_id in listener.event_ids:
                self.listeners[event_id].append(listener.fn)

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


class SimpleEventEmitter(BaseEventEmitterBackend):
    """Event emitter the works only in the current process"""

    async def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g 'my_event'.
            *args: args to pass to the listener(s).
            **kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        if listeners := self.listeners.get(event_id):
            if len(listeners) > 1:
                async with create_task_group() as task_group:
                    for listener in listeners:
                        task_group.start_soon(partial(listener, *args, **kwargs))
            else:
                await listeners[0](*args, **kwargs)
        else:
            raise ImproperlyConfiguredException(f"no event listeners are registered for the event ID: {event_id}")
