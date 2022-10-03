import atexit
from io import StringIO
from logging import StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, List, Optional

from starlite.logging.utils import resolve_handlers


class QueueListenerHandler(QueueHandler):
    def __init__(self, handlers: Optional[List[Any]] = None) -> None:
        """Configures queue listener and handler to support non-blocking
        logging configuration.

        Args:
            handlers: Optional 'ConvertingList'
        """
        super().__init__(Queue(-1))
        if handlers:
            handlers = resolve_handlers(handlers)
        else:
            handlers = [StreamHandler(StringIO())]
        self.listener = QueueListener(self.queue, *handlers)
        self.listener.start()

        atexit.register(self.listener.stop)
