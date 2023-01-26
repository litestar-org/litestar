from typing import TYPE_CHECKING, Any, List, Union

from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from starlite.types import AnyCallable


class EventListener:
    """Decorator for event listeners"""

    __slots__ = ("event_ids", "fn")

    fn: "AsyncCallable[Any, Any]"

    def __init__(self, event_id: Union[str, List[str]]):
        """Create a decorator for event handlers.

        :param event_id: The id of the event to listen to or a list of event ids to listen to.
        """
        self.event_ids: List[str] = [event_id] if isinstance(event_id, str) else event_id

    def __call__(self, fn: "AnyCallable") -> "EventListener":
        """Decorate a callable by wrapping it inside an instance of EventListener.

        :param fn: Callable to decorate.
        :return: An instance of EventListener
        """
        if not callable(fn):
            raise ImproperlyConfiguredException("EventListener instance should be called as a decorator")

        self.fn = AsyncCallable(fn)

        return self


listener = EventListener
