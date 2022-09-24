import atexit
from io import StringIO
from logging import StreamHandler
from queue import Queue

from picologging.handlers import QueueHandler, QueueListener


class QueueListenerHandler(QueueHandler):  # type: ignore[misc]
    def __init__(self) -> None:
        """Configures queue listener and handler to support non-blocking
        logging configuration.

        Notes:
            - Requires `picologging` to be installed.
        """
        super().__init__(Queue(-1))
        self.listener = QueueListener(self.queue, StreamHandler(StringIO()))
        self.listener.start()

        atexit.register(self.listener.stop)
