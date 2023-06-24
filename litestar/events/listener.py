from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils import AsyncCallable

__all__ = ("EventListener", "listener")


if TYPE_CHECKING:
    from litestar.types import AnyCallable


class EventListener:
    """Decorator for event listeners"""

    __slots__ = ("event_ids", "fn", "listener_id")

    fn: AsyncCallable[Any, Any]

    def __init__(self, *event_ids: str) -> None:
        """Create a decorator for event handlers.

        Args:
            *event_ids: The id of the event to listen to or a list of
                event ids to listen to.
        """
        self.event_ids: frozenset[str] = frozenset(event_ids)

    def __call__(self, fn: AnyCallable) -> EventListener:
        """Decorate a callable by wrapping it inside an instance of EventListener.

        Args:
            fn: Callable to decorate.

        Returns:
            An instance of EventListener
        """
        if not callable(fn):
            raise ImproperlyConfiguredException("EventListener instance should be called as a decorator on a callable")

        self.fn = AsyncCallable(fn)

        return self

    def __hash__(self) -> int:
        return hash(self.event_ids) + hash(self.fn)


listener = EventListener
