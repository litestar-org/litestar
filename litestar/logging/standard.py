from __future__ import annotations

import atexit
import sys
from logging import StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any

from litestar.logging._utils import resolve_handlers

__all__ = ("QueueListenerHandler",)


if sys.version_info < (3, 12):

    class QueueListenerHandler(QueueHandler):
        """Configure queue listener and handler to support non-blocking logging configuration."""

        def __init__(self, handlers: list[Any] | None = None) -> None:
            """Initialize `?QueueListenerHandler`.

            Args:
                handlers: Optional 'ConvertingList'
            """
            super().__init__(Queue(-1))
            handlers = resolve_handlers(handlers) if handlers else [StreamHandler()]
            self.listener = QueueListener(self.queue, *handlers)
            self.listener.start()

            atexit.register(self.listener.stop)

else:
    QueueListenerHandler = QueueHandler
