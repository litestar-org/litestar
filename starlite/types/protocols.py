from typing import Any

from typing_extensions import Protocol


class Logger(Protocol):  # pragma: no cover
    def debug(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'DEBUG' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def info(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'INFO' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def warning(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARN' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def warn(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARN' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def error(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'ERROR' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def fatal(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'CRITICAL' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def exception(self, event: str, **kwargs: Any) -> Any:
        """Logs a message with level 'ERROR' on this logger. The arguments are
        interpreted as for debug(). Exception info is added to the logging
        message.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """

    def critical(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'CRITICAL' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
