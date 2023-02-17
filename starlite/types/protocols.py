from typing import Any, Protocol


class Logger(Protocol):  # pragma: no cover
    """Logger protocol."""

    def debug(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'DEBUG' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def info(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def warning(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'WARNING' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def warn(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'WARN' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def error(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'ERROR' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def fatal(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'FATAL' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def exception(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Log a message with level 'ERROR' on this logger. The arguments are interpreted as for debug(). Exception info
        is added to the logging message.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def critical(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """
