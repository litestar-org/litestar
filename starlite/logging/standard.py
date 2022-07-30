from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, List

from starlite.logging import resolve_handlers


class QueueListenerHandler(QueueHandler):
    """
    Configures queue listener and handler to support non-blocking logging configuration.
    """

    def __init__(self, handlers: List[Any], respect_handler_level: bool = False, queue: Queue = Queue(-1)):
        super().__init__(queue)
        self.handlers = resolve_handlers(handlers)
        self._listener: QueueListener = QueueListener(
            self.queue, *self.handlers, respect_handler_level=respect_handler_level
        )
        self._listener.start()
