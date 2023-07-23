from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from litestar._parsers import parse_cookie_string, parse_headers, parse_query_string
from litestar.datastructures.headers import Headers
from litestar.datastructures.multi_dicts import MultiDict
from litestar.datastructures.state import State
from litestar.datastructures.url import URL, Address, make_absolute_url
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.empty import Empty

__all__ = ("ASGIConnection", "empty_receive", "empty_send")


if TYPE_CHECKING:
    from typing import NoReturn

    from litestar.app import Litestar
    from litestar.types import DataContainerType, EmptyType
    from litestar.types.asgi_types import Message, Receive, Scope, Send
    from litestar.types.protocols import Logger

UserT = TypeVar("UserT")
AuthT = TypeVar("AuthT")
HandlerT = TypeVar("HandlerT")
StateT = TypeVar("StateT", bound=State)


async def empty_receive() -> NoReturn:  # pragma: no cover
    """Raise a ``RuntimeError``.

    Serves as a placeholder ``send`` function.

    Raises:
        RuntimeError
    """
    raise RuntimeError()


async def empty_send(_: Message) -> NoReturn:  # pragma: no cover
    """Raise a ``RuntimeError``.

    Serves as a placeholder ``send`` function.

    Args:
        _: An ASGI message

    Raises:
        RuntimeError
    """
    raise RuntimeError()


class ASGIConnection(Generic[HandlerT, UserT, AuthT, StateT]):
    """The base ASGI connection container."""

    __slots__ = ("scope", "receive", "send", "_base_url", "_url", "_parsed_query", "_headers", "_cookies")

    scope: Scope
    """The ASGI scope attached to the connection."""
    receive: Receive
    """The ASGI receive function."""
    send: Send
    """The ASGI send function."""

    def __init__(self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send) -> None:
        """Initialize ``ASGIConnection``.

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
    def app(self) -> Litestar:
        """Return the ``app`` for this connection.

        Returns:
            The :class:`Litestar <litestar.app.Litestar>` application instance
        """
        return self.scope["app"]

    @property
    def route_handler(self) -> HandlerT:
        """Return the ``route_handler`` for this connection.

        Returns:
            The target route handler instance.
        """
        return cast("HandlerT", self.scope["route_handler"])

    @property
    def state(self) -> StateT:
        """Return the ``State`` of this connection.

        Returns:
            A State instance constructed from the scope["state"] value.
        """
        return cast("StateT", State(self.scope["state"]))

    @property
    def url(self) -> URL:
        """Return the URL of this connection's ``Scope``.

        Returns:
            A URL instance constructed from the request's scope.
        """
        if self._url is Empty:
            self._url = self.scope["_url"] = URL.from_scope(self.scope)  # type: ignore[typeddict-unknown-key]

        return cast("URL", self._url)

    @property
    def base_url(self) -> URL:
        """Return the base URL of this connection's ``Scope``.

        Returns:
            A URL instance constructed from the request's scope, representing only the base part
            (host + domain + prefix) of the request.
        """
        if self._base_url is Empty:
            scope = {
                **self.scope,
                "path": "/",
                "query_string": b"",
                "root_path": self.scope.get("app_root_path") or self.scope.get("root_path", ""),
            }
            self._base_url = self.scope["_base_url"] = URL.from_scope(cast("Scope", scope))  # type: ignore[typeddict-unknown-key]

        return cast("URL", self._base_url)

    @property
    def headers(self) -> Headers:
        """Return the headers of this connection's ``Scope``.

        Returns:
            A Headers instance with the request's scope["headers"] value.
        """
        if self._headers is Empty:
            self.scope.setdefault("headers", [])
            self._headers = self.scope["_headers"] = parse_headers(tuple(self.scope["headers"]))  # type: ignore[typeddict-unknown-key]

        return Headers(self._headers)

    @property
    def query_params(self) -> MultiDict[Any]:
        """Return the query parameters of this connection's ``Scope``.

        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        if self._parsed_query is Empty:
            self._parsed_query = self.scope["_parsed_query"] = parse_query_string(self.scope.get("query_string", b""))  # type: ignore

        return MultiDict(self._parsed_query)

    @property
    def path_params(self) -> dict[str, Any]:
        """Return the ``path_params`` of this connection's ``Scope``.

        Returns:
            A string keyed dictionary of path parameter values.
        """
        return self.scope["path_params"]

    @property
    def cookies(self) -> dict[str, str]:
        """Return the ``cookies`` of this connection's ``Scope``.

        Returns:
            Returns any cookies stored in the header as a parsed dictionary.
        """
        if self._cookies is Empty:
            cookies: dict[str, str] = {}
            if cookie_header := self.headers.get("cookie"):
                cookies = parse_cookie_string(cookie_header)

            self._cookies = self.scope["_cookies"] = cookies  # type: ignore[typeddict-unknown-key]

        return cast("dict[str, str]", self._cookies)

    @property
    def client(self) -> Address | None:
        """Return the ``client`` data of this connection's ``Scope``.

        Returns:
            A two tuple of the host name and port number.
        """
        client = self.scope.get("client")
        return Address(*client) if client else None

    @property
    def auth(self) -> AuthT:
        """Return the ``auth`` data of this connection's ``Scope``.

        Raises:
            ImproperlyConfiguredException: If ``auth`` is not set in scope via an ``AuthMiddleware``, raises an exception

        Returns:
            A type correlating to the generic variable Auth.
        """
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")

        return cast("AuthT", self.scope["auth"])

    @property
    def user(self) -> UserT:
        """Return the ``user`` data of this connection's ``Scope``.

        Raises:
            ImproperlyConfiguredException: If ``user`` is not set in scope via an ``AuthMiddleware``, raises an exception

        Returns:
            A type correlating to the generic variable User.
        """
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")

        return cast("UserT", self.scope["user"])

    @property
    def session(self) -> dict[str, Any]:
        """Return the session for this connection if a session was previously set in the ``Scope``

        Returns:
            A dictionary representing the session value - if existing.

        Raises:
            ImproperlyConfiguredException: if session is not set in scope.
        """
        if "session" not in self.scope:
            raise ImproperlyConfiguredException(
                "'session' is not defined in scope, install a SessionMiddleware to set it"
            )

        return cast("dict[str, Any]", self.scope["session"])

    @property
    def logger(self) -> Logger:
        """Return the ``Logger`` instance for this connection.

        Returns:
            A ``Logger`` instance.

        Raises:
            ImproperlyConfiguredException: if ``log_config`` has not been passed to the Litestar constructor.
        """
        return self.app.get_logger()

    def set_session(self, value: dict[str, Any] | DataContainerType | EmptyType) -> None:
        """Set the session in the connection's ``Scope``.

        If the :class:`SessionMiddleware <.middleware.session.base.SessionMiddleware>` is enabled, the session will be added
        to the response as a cookie header.

        Args:
            value: Dictionary or pydantic model instance for the session data.

        Returns:
            None.
        """
        self.scope["session"] = value

    def clear_session(self) -> None:
        """Remove the session from the connection's ``Scope``.

        If the :class:`Litestar SessionMiddleware <.middleware.session.base.SessionMiddleware>` is enabled, this will cause
        the session data to be cleared.

        Returns:
            None.
        """
        self.scope["session"] = Empty

    def url_for(self, name: str, **path_parameters: Any) -> str:
        """Return the url for a given route handler name.

        Args:
            name: The ``name`` of the request route handler.
            **path_parameters: Values for path parameters in the route

        Raises:
            NoRouteMatchFoundException: If route with ``name`` does not exist, path parameters are missing or have a
                wrong type.

        Returns:
            A string representing the absolute url of the route handler.
        """
        litestar_instance = self.scope["app"]
        url_path = litestar_instance.route_reverse(name, **path_parameters)

        return make_absolute_url(url_path, self.base_url)

    def url_for_static_asset(self, name: str, file_path: str) -> str:
        """Receives a static files handler name, an asset file path and returns resolved absolute url to the asset.

        Args:
            name: A static handler unique name.
            file_path: a string containing path to an asset.

        Raises:
            NoRouteMatchFoundException: If static files handler with ``name`` does not exist.

        Returns:
            A string representing absolute url to the asset.
        """
        litestar_instance = self.scope["app"]
        url_path = litestar_instance.url_for_static_asset(name, file_path)

        return make_absolute_url(url_path, self.base_url)
