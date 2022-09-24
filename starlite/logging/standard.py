import atexit
from io import StringIO
from logging import StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue


class QueueListenerHandler(QueueHandler):
    def __init__(self) -> None:
        """Configures queue listener and handler to support non-blocking
        logging configuration."""
        super().__init__(Queue(-1))
        self.listener = QueueListener(self.queue, StreamHandler(StringIO()))
        self.listener.start()

        atexit.register(self.listener.stop)
