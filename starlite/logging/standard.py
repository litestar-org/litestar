import atexit
from logging import StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, List, Optional

from starlite.logging.utils import resolve_handlers


class QueueListenerHandler(QueueHandler):
    """Configure queue listener and handler to support non-blocking logging configuration."""

    def __init__(self, handlers: Optional[List[Any]] = None) -> None:
        """Initialize `?QueueListenerHandler`.

        Args:
            handlers: Optional 'ConvertingList'
        """
        super().__init__(Queue(-1))
        if handlers:
            handlers = resolve_handlers(handlers)
        else:
            handlers = [StreamHandler()]
        self.listener = QueueListener(self.queue, *handlers)
        self.listener.start()

        atexit.register(self.listener.stop)
