import atexit
from queue import Queue
from typing import Any, List, Optional

from starlite.exceptions import MissingDependencyException
from starlite.logging.utils import resolve_handlers

try:
    from picologging import StreamHandler
    from picologging.handlers import QueueHandler, QueueListener
except ImportError as e:
    raise MissingDependencyException("picologging is not installed") from e


class QueueListenerHandler(QueueHandler):
    """Configure queue listener and handler to support non-blocking logging configuration."""

    def __init__(self, handlers: Optional[List[Any]] = None) -> None:
        """Initialize `QueueListenerHandler`.

        Args:
            handlers: Optional 'ConvertingList'

        Notes:
            - Requires `picologging` to be installed.
        """
        super().__init__(Queue(-1))
        if handlers:
            handlers = resolve_handlers(handlers)
        else:
            handlers = [StreamHandler()]
        self.listener = QueueListener(self.queue, *handlers)
        self.listener.start()

        atexit.register(self.listener.stop)
