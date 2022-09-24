import atexit
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, List

from starlite.logging.utils import resolve_handlers


class QueueListenerHandler(QueueHandler):
    def __init__(self, handlers: List[Any]) -> None:
        """Configures queue listener and handler to support non-blocking
        logging configuration.

        Args:
            handlers (list): list of handler names.
        """
        super().__init__(Queue(-1))
        self.listener = QueueListener(self.queue, *resolve_handlers(handlers))
        self.listener.start()

        atexit.register(self.listener.stop)
