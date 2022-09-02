from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, List


class QueueListenerHandler(QueueHandler):
    """Configures queue listener and handler to support non-blocking logging
    configuration."""

    def __init__(self, handlers: List[Any], respect_handler_level: bool = False, queue: Queue = Queue(-1)):
        """Configures queue listener and handler to support non-blocking
        logging configuration.

        Args:
            handlers (list): list of handler names.
            respect_handler_level (bool): A handler's level is respected (compared with the level for the message) when
                deciding whether to pass messages to that handler.
        """
        super().__init__(queue)
        self.handlers = resolve_handlers(handlers)
        self._listener: QueueListener = QueueListener(
            self.queue, *self.handlers, respect_handler_level=respect_handler_level
        )
        self._listener.start()


def resolve_handlers(handlers: List[Any]) -> List[Any]:
    """Converts list of string of handlers to the object of respective handler.

    Indexing the list performs the evaluation of the object.
    """
    return [handlers[i] for i in range(len(handlers))]
