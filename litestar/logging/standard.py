from __future__ import annotations

import atexit
import sys
from logging import Handler, LogRecord, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any

from litestar.logging._utils import resolve_handlers

__all__ = ("QueueListenerHandler",)


if sys.version_info < (3, 12):

    class QueueListenerHandler(QueueHandler):
        """Configure queue listener and handler to support non-blocking logging configuration."""

        def __init__(self, handlers: list[Any] | None = None) -> None:
            """Initialize `QueueListenerHandler`.

            Args:
                handlers: Optional 'ConvertingList'
            """
            super().__init__(Queue(-1))
            handlers = resolve_handlers(handlers) if handlers else [StreamHandler()]
            self.listener = QueueListener(self.queue, *handlers)
            self.listener.start()

            atexit.register(self.listener.stop)

else:

    class LoggingQueueListener(QueueListener):
        """Custom ``QueueListener`` which starts and stops the listening process."""

        def __init__(self, queue: Queue[LogRecord], *handlers: Handler, respect_handler_level: bool = False) -> None:
            """Initialize ``LoggingQueueListener``.

            Args:
                queue: The queue to send messages to
                *handlers: A list of handlers which will handle entries placed on the queue
                respect_handler_level: If ``respect_handler_level`` is ``True``, a handler's level is respected (compared with the level for the message) when deciding whether to pass messages to that handler
            """
            super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
            self.start()
            atexit.register(self.stop)
