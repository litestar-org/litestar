from __future__ import annotations

import atexit
from queue import Queue
from typing import Any

from litestar.exceptions import MissingDependencyException
from litestar.logging._utils import resolve_handlers

__all__ = ("QueueListenerHandler",)


try:
    import picologging  # noqa: F401 # pyright: ignore[reportMissingImports]
except ImportError as e:
    raise MissingDependencyException("picologging") from e

from picologging import StreamHandler  # pyright: ignore[reportMissingImports]
from picologging.handlers import QueueHandler, QueueListener  # pyright: ignore[reportMissingImports]


class QueueListenerHandler(QueueHandler):  # type: ignore[misc,unused-ignore]
    """Configure queue listener and handler to support non-blocking logging configuration."""

    def __init__(self, handlers: list[Any] | None = None) -> None:
        """Initialize ``QueueListenerHandler``.

        Args:
            handlers: Optional 'ConvertingList'

        Notes:
            - Requires ``picologging`` to be installed.
        """
        super().__init__(Queue(-1))
        handlers = resolve_handlers(handlers) if handlers else [StreamHandler()]  # pyright: ignore[reportGeneralTypeIssues]
        self.listener = QueueListener(self.queue, *handlers)  # pyright: ignore[reportGeneralTypeIssues]
        self.listener.start()

        atexit.register(self.listener.stop)
