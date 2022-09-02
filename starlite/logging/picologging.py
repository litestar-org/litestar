from queue import Queue
from typing import Any, List

from picologging.handlers import QueueHandler, QueueListener

from starlite.logging.standard import resolve_handlers


class QueueListenerHandler(QueueHandler):  # type: ignore
    def __init__(self, handlers: List[Any], respect_handler_level: bool = False, queue: Queue = Queue(-1)):
        """Configures queue listener and handler to support non-blocking
        logging configuration.

        Requires `picologging`, install with:
        ```shell
        $ pip install starlite[picologging]
        ```

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
