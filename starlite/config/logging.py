from logging import Logger, config, getLogger
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Type,
    Union,
)

from pydantic import BaseModel
from typing_extensions import Literal

try:
    from picologging import config as picologging_config
except ImportError:
    picologging_config = None

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.middleware.base import DefineMiddleware, MiddlewareProtocol

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LoggingMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: "ASGIApp",
        config: "LoggingConfig",  # pylint: disable=redefined-outer-name
    ):
        """Logging Middleware class.

        This Middleware log incoming request and outgoing response. It use classic logging library.

        Examples:

            ```python
            from starlite import Starlite, Request, get
            from starlite.config.logging import LoggingConfig

            logging_config = LoggingConfig(middleware_log_request=False)


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[logging_config.middleware])
            ```

        You can use another logging library by subclassing LoggingMiddleware.

        Examples:

            ```python
            from starlite import Starlite, Request, get
            from starlite.config.logging import LoggingMiddleware, LoggingConfig


            class PicologgingMiddleware(LoggingMiddleware):
                def get_logger(self):
                    import picologging as logging

                    return logging.getLogger("custom.path.to.logging")


            logging_config = LoggingConfig(
                middleware_log_request=False, middleware_class=PicologgingMiddleware
            )


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[logging_config.middleware])
            ```

        Args:
            app: The 'next' ASGI app to call.
            config: The LoggingConfig instance.
        """
        super().__init__(app)
        self.app = app
        self.config = config
        self.logger = self.get_logger()

    def get_logger(self) -> Logger:
        """Return a logger which will be used to log incoming and outgoing
        request and response. Use middleware_logger_name from config to set the
        name of the logger.

        Returns:
            An instance of logging.Logger
        """
        return getLogger(self.config.middleware_logger_name)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request: Request = Request(scope=scope)
        self.log_request(request, scope)

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == "http.response.start":
                self.log_response(request, message)
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def log_request(self, request: "Request", scope: "Scope") -> None:
        """Log following line when request is received.

        '{hostname}:{port} - {method} {path} {scheme}/{http_version} incoming'
        """
        if self.config.middleware_log_request:
            self.logger.info(
                "%s:%s - %s %s %s/%s incoming",
                request.base_url.hostname,
                request.base_url.port or "",
                request.method.upper(),
                request.base_url.path,
                request.base_url.scheme.upper(),
                request.scope.get("http_version", ""),
            )

    def log_response(self, request: "Request", message: "Message") -> None:
        """Log following line when response is ready to be sent to client.

        '{hostname}:{port} - {method} {path} {scheme}/{http_version} {result}'
        """
        if self.config.middleware_log_response:
            self.logger.info(
                "%s:%s - %s %s %s/%s %s",
                request.base_url.hostname,
                request.base_url.port or "",
                request.method.upper(),
                request.base_url.path,
                request.base_url.scheme.upper(),
                request.scope.get("http_version", ""),
                message.get("status", "notset"),
            )


class LoggingConfig(BaseModel):
    """Convenience `pydantic` model for configuring logging.

    For detailed instructions consult [standard library docs](https://docs.python.org/3/library/logging.config.html).
    """

    version: Literal[1] = 1
    """The only valid value at present is 1."""
    incremental: bool = False
    """Whether the configuration is to be interpreted as incremental to the existing configuration. """
    disable_existing_loggers: bool = False
    """Whether any existing non-root loggers are to be disabled."""
    filters: Optional[Dict[str, Dict[str, Any]]] = None
    """A dict in which each key is a filter id and each value is a dict describing how to configure the corresponding Filter instance."""
    propagate: bool = True
    """If messages must propagate to handlers higher up the logger hierarchy from this logger."""
    formatters: Dict[str, Dict[str, Any]] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
        "queue_listener": {"class": "starlite.QueueListenerHandler", "handlers": ["cfg://handlers.console"]},
    }
    """A dict in which each key is a handler id and each value is a dict describing how to configure the corresponding Handler instance."""
    loggers: Dict[str, Dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        },
    }
    """A dict in which each key is a logger name and each value is a dict describing how to configure the corresponding Logger instance."""
    root: Dict[str, Union[Dict[str, Any], List[Any], str]] = {"handlers": ["queue_listener"], "level": "INFO"}
    """This will be the configuration for the root logger. Processing of the configuration will be as for any logger,
    except that the propagate setting will not be applicable."""

    # Below all config options for the logging middleware
    middleware_logger_name: str = "starlite.middleware.logging"
    """The name of the fetched logger"""

    middleware_log_request: bool = True
    """Set to, False to not to log entry request"""

    middleware_log_response: bool = True
    """Set to, False to not to log sent response"""

    middleware_class: Type[LoggingMiddleware] = LoggingMiddleware
    """Change the class if you want to use another middleware. New class has to inherit from LoggingMiddleware"""

    def configure(self) -> None:
        """Configured logger with the given configuration.

        If the logger class contains the word `picologging`, we try to
        import and set the dictConfig
        """
        # remove middleware parameters before initializing logging
        dict_config = {k: v for k, v in self.dict(exclude_none=True).items() if not k.startswith("middleware_")}

        for logging_class in find_keys(self.handlers, "class"):
            if "picologging" in logging_class and picologging_config:
                picologging_config.dictConfig(dict_config)
                break

        config.dictConfig(dict_config)

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from os import urandom

            from starlite import Starlite, Request, get
            from starlite.config.logging import LoggingConfig

            logging_config = LoggingConfig()


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[logging_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)


def find_keys(node: Union[List, Dict], key: str) -> Generator[Iterable, None, None]:
    """Find Nested Keys with name
    Search a dictionary for the presence of key
    Args:
        node (Union[List, Dict]): a dictionary to search
        key (str): the dictionary key to find

    Yields:
        Generator[Iterable, None, None]: Value of dictionary key
    """
    if isinstance(node, list):
        for list_entry in node:
            yield from find_keys(list_entry, key)
    elif isinstance(node, dict):
        if key in node:
            yield node[key]
        for dict_entry in node.values():
            yield from find_keys(dict_entry, key)
