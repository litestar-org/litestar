from atexit import register
from logging.config import ConvertingList  # type: ignore
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import List


def _resolve_handlers(handlers: List[str]) -> List:
    """
    Converts list of string of handlers to the object of respective handler.
    Indexing the list performs the evaluation of the object.
    """
    if not isinstance(handlers, ConvertingList):
        return handlers

    return [handlers[i] for i in range(len(handlers))]


class QueueListenerHandler(QueueHandler):
    """
    Configures queue listener and handler to support non-blocking logging configuration.
    """

    def __init__(
        self, handlers: List, respect_handler_level: bool = False, auto_run: bool = True, queue: Queue = Queue(-1)
    ):
        super().__init__(queue)
        self.handlers = _resolve_handlers(handlers)
        self._listener: QueueListener = QueueListener(
            self.queue, *self.handlers, respect_handler_level=respect_handler_level
        )
        if auto_run:
            self.start()
            register(self.stop)

    def start(self) -> None:
        """
        starts the listener.
        """
        self._listener.start()

    def stop(self) -> None:
        """
        Manually stop a listener.
        """
        self._listener.stop()
