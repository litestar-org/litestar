from typing import Any, overload

from typing_extensions import Protocol


class Logger(Protocol):  # pragma: no cover
    @overload
    def debug(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'DEBUG' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def debug(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'DEBUG' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def debug(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'DEBUG' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def info(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'INFO' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def info(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def info(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def warning(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARNING' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def warning(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'WARNING' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def warning(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARNING' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def warn(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARN' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def warn(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'WARN' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def warn(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'WARN' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def error(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'ERROR' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def error(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'ERROR' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def error(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'ERROR' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def fatal(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'FATAL' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def fatal(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'FATAL' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def fatal(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'FATAL' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def exception(self, event: str, **kwargs: Any) -> Any:
        """Logs a message with level 'ERROR' on this logger. The arguments are
        interpreted as for debug(). Exception info is added to the logging
        message.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def exception(self, event: str, *args: Any) -> Any:
        """Logs a message with level 'ERROR' on this logger. The arguments are
        interpreted as for debug(). Exception info is added to the logging
        message.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def exception(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Logs a message with level 'ERROR' on this logger. The arguments are
        interpreted as for debug(). Exception info is added to the logging
        message.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    @overload
    def critical(self, event: str, **kwargs: Any) -> Any:
        """Outputs a log message at 'CRITICAL' level.

        Args:
             event: Log message.
             **kwargs: Any kwargs.
        """
        ...

    @overload
    def critical(self, event: str, *args: Any) -> Any:
        """Outputs a log message at 'CRITICAL' level.

        Args:
             event: Log message.
             *args: Any args.
        """
        ...

    def critical(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Outputs a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """
