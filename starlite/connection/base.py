from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

from starlette.datastructures import URL, Address, Headers, URLPath
from starlette.requests import cookie_parser

from starlite.datastructures.state import State
from starlite.exceptions import ImproperlyConfiguredException
from starlite.parsers import parse_query_params
from starlite.types.empty import Empty

if TYPE_CHECKING:
    from typing import MutableMapping

    from pydantic import BaseModel

    from starlite.app import Starlite
    from starlite.cache import Cache
    from starlite.types.asgi_types import Message, Receive, Scope, Send
    from starlite.types.protocols import Logger

User = TypeVar("User")
Auth = TypeVar("Auth")
Handler = TypeVar("Handler")


async def empty_receive() -> Any:  # pragma: no cover
    """Placeholder value.

    Raises:
        RuntimeError
    """
    raise RuntimeError()


async def empty_send(_: "Message") -> None:  # pragma: no cover
    """Placeholder value.

    Args:
        _: An ASGI message

    Raises:
        RuntimeError
    """
    raise RuntimeError()


class ASGIConnection(Generic[Handler, User, Auth]):
    __slots__ = ("scope", "receive", "send", "_base_url", "_url", "_parsed_query", "_headers", "_cookies")

    scope: "Scope"
    """
    The ASGI scope attached to the connection.
    """
    receive: "Receive"
    """
    The ASGI receive function.
    """
    send: "Send"
    """
    The ASGI send function.
    """

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
        """The base ASGI connection container.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        self.scope = scope
        self.receive = receive
        self.send = send
        self._base_url: Any = scope.get("_base_url", Empty)
        self._url: Any = scope.get("_url", Empty)
        self._parsed_query: Any = scope.get("_parsed_query", Empty)
        self._cookies: Any = scope.get("_cookies", Empty)
        self._headers: Any = scope.get("_headers", Empty)

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return self.scope["app"]

    @property
    def route_handler(self) -> Handler:
        """
        Returns:
            The target route handler instance.
        """
        return cast("Handler", self.scope["route_handler"])

    @property
    def state(self) -> State:
        """

        Returns:
            A State instance constructed from the scope["state"] value.
        """
        return State(self.scope["state"])

    @property
    def url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope.
        """
        if self._url is Empty:
            self._url = self.scope["_url"] = URL(scope=cast("MutableMapping[str, Any]", self.scope))  # type: ignore[typeddict-item]
        return cast("URL", self._url)

    @property
    def base_url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope, representing only the base part
            (host + domain + prefix) of the request.
        """
        if self._base_url is Empty:
            self._base_url = self.scope["_base_url"] = URL(  # type: ignore[typeddict-item]
                scope={
                    **self.scope,
                    "path": "/",
                    "query_string": b"",
                    "root_path": self.scope.get("app_root_path") or self.scope.get("root_path", ""),
                }
            )
        return cast("URL", self._base_url)

    @property
    def headers(self) -> Headers:
        """

        Returns:
            A Headers instance with the request's scope["headers"] value.
        """
        if self._headers is Empty:
            self._headers = self.scope["_headers"] = Headers(scope=self.scope)  # type: ignore[typeddict-item]
        return cast("Headers", self._headers)

    @property
    def query_params(self) -> Dict[str, List[str]]:
        """
        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        if self._parsed_query is Empty:
            self._parsed_query = self.scope["_parsed_query"] = parse_query_params(self.scope.get("query_string", b""))  # type: ignore[typeddict-item]
        return cast("Dict[str, List[str]]", self._parsed_query)

    @property
    def path_params(self) -> Dict[str, Any]:
        """

        Returns:
            A string keyed dictionary of path parameter values.
        """
        return self.scope["path_params"]

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Returns:
            Returns any cookies stored in the header as a parsed dictionary.
        """
        if self._cookies is Empty:
            cookies: Dict[str, str] = {}
            cookie_header = self.headers.get("cookie")
            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = self.scope["_cookies"] = cookies  # type: ignore[typeddict-item]
        return cast("Dict[str, str]", self._cookies)

    @property
    def client(self) -> Optional[Address]:
        """

        Returns:
            A two tuple of the host name and port number.
        """
        client = self.scope.get("client")
        return Address(*client) if client else None

    @property
    def auth(self) -> Auth:
        """Allows access to auth data.

        Raises:
            ImproperlyConfiguredException: If 'auth' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable Auth.
        """
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])

    @property
    def user(self) -> User:
        """Allows access to user data.

        Raises:
            ImproperlyConfiguredException: If 'user' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable User.
        """
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast("User", self.scope["user"])

    @property
    def session(self) -> Dict[str, Any]:
        """
        Returns:
            A dictionary representing the session value - if existing.

        Raises:
            ImproperlyConfiguredException: if session is not set in scope.
        """
        if "session" not in self.scope:
            raise ImproperlyConfiguredException(
                "'session' is not defined in scope, install a SessionMiddleware to set it"
            )
        return cast("Dict[str, Any]", self.scope["session"])

    @property
    def logger(self) -> "Logger":
        """

        Returns:
            A 'Logger' instance.

        Raises:
            ImproperlyConfiguredException: if 'log_config' has not been passed to the Starlite constructor.
        """
        return self.app.get_logger()

    @property
    def cache(self) -> "Cache":
        """

        Returns:
            A 'Cache' instance.
        """
        return self.app.cache

    def set_session(self, value: Union[Dict[str, Any], "BaseModel"]) -> None:
        """Helper method to set the session in scope.

        If the [Starlite SessionMiddleware][starlite.middleware.session.SessionMiddleware] is
        enabled, the session will be added to the response as a cookie header.

        Args:
            value: Dictionary or pydantic model instance for the session data.

        Returns:
            None.
        """
        self.scope["session"] = value

    def clear_session(self) -> None:
        """Helper method to remove the session from scope.

        If the [Starlite SessionMiddleware][starlite.middleware.session.SessionMiddleware] is
        enabled, this will cause the session data to be cleared.

        Returns:
            None.
        """
        self.scope["session"] = {}

    def url_for(self, name: str, **path_parameters: Dict[str, Any]) -> Optional[str]:
        """

        Args:
            name: The 'name' of the request route handler.
            **path_parameters: Values for path parameters in the route

        Raises:
            ValidationException: If path parameters are missing in **path_parameters or have wrong type.

        Returns:
            If a route handler with the given name is found, it returns a string representing the absolute url of the route handler.
        """
        starlite_instance = self.scope["app"]
        url_path = starlite_instance.route_reverse(name, **path_parameters)
        if url_path:
            return URLPath(url_path).make_absolute_url(self.base_url)
        return None
