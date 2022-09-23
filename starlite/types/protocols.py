from typing import Any, Protocol


class Logger(Protocol):  # pragma: no cover
    def debug(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'debug' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def info(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'info' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def warning(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'warn' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def warn(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'warn' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def error(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'error' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def err(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'error' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def fatal(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'ical' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def exception(self, event: str, **kwargs: Any) -> Any:
        """
        Logs a message with level 'error' on this logger. The arguments are interpreted as for debug(). Exception info is added to the logging message. This method should only be called from an exception handler.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """

    def critical(self, event: str, **kwargs: Any) -> Any:
        """
        Outputs a log message at 'ical' level.
        Args:
             event: String value to log
             **kwargs: Any kwargs.
        """
