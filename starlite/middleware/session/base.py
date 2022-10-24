import abc
import secrets
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import BaseConfig, BaseModel, conint, conlist, constr
from starlette.datastructures import MutableHeaders
from typing_extensions import Literal

from starlite import ASGIConnection, Cookie, DefineMiddleware
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Message, Receive, Scope, Send


ONE_DAY_IN_SECONDS = 60 * 60 * 24


class BaseBackendConfig(BaseModel):
    _backend_class: ClassVar[Type["SessionBackend"]]

    """Configuration for Session middleware cookies."""

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    key: constr(min_length=1, max_length=256) = "session"  # type: ignore[valid-type]
    """
    Key to use for the cookie inside the header,
    e.g. `session=<data>` where 'session' is the cookie key and <data> is the session data.

    Notes:
        - If a session cookie exceeds 4KB in size it is split. In this case the key will be of the format
            'session-{segment number}'.
    """
    max_age: conint(ge=1) = ONE_DAY_IN_SECONDS * 14  # type: ignore[valid-type]
    """Maximal age of the cookie before its invalidated."""
    scopes: conlist(Literal["http", "websocket"], min_items=1, max_items=2) = ["http", "websocket"]  # type: ignore[valid-type]
    """Scopes for the middleware - options are 'http' and 'websocket' with the default being both"""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: str | None = None
    """Domain for which the cookie is valid."""
    secure: bool = False
    """Https is required for the cookie."""
    httponly: bool = True
    """Forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""

    @property
    def backend(self) -> "SessionBackend":
        return self._backend_class(config=self)

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from os import urandom

            from starlite import Starlite, Request, get
            from starlite.middleware.session import SessionCookieConfig

            session_config = SessionCookieConfig(secret=urandom(16))


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[session_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(SessionMiddleware, backend=self.backend)


class ServerSideSessionConfig(BaseBackendConfig):
    session_id_bytes: int = 32
    identity_mode: Literal["cookie", "header"] = "cookie"


Config = TypeVar("Config", bound=BaseBackendConfig)
ServerConfig = TypeVar("ServerConfig", bound=ServerSideSessionConfig)


class SessionBackend(abc.ABC, Generic[Config]):
    def __init__(self, config: Config) -> None:
        self.config = config

    @staticmethod
    def serialise_data(data: Any, scope: Optional["Scope"] = None) -> bytes:
        """Serialise data into bytes for storage in the backend.

        The serialiser will be
        gathered from `scope` and fall back to [default_serializer][starlite.utils.default_serializer]
        """
        serializer = (get_serializer_from_scope(scope) if scope else None) or default_serializer
        return dumps(data, default=serializer, option=OPT_SERIALIZE_NUMPY)

    @staticmethod
    def deserialise_data(data: Any) -> Dict[str, Any]:
        return cast("Dict[str, Any]", loads(data))

    @abc.abstractmethod
    async def store_in_message(self, message: "Message", connection: ASGIConnection) -> None:
        pass

    @abc.abstractmethod
    async def load_from_connection(self, connection: ASGIConnection) -> Dict[str, Any]:
        pass


class ServerSideBackend(Generic[ServerConfig], SessionBackend[ServerConfig]):
    def __init__(self, config: ServerConfig) -> None:
        """Starlite session middleware for storing session data server-side."""

        super().__init__(config=config)

    @abc.abstractmethod
    async def get(self, session_id: str) -> Union[bytes, str, Dict[str, Any], None]:
        """Retrieve data associate with `session_id`.

        If no data for the given `session_id` exists, return an empty
        dict
        """

    @abc.abstractmethod
    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` under the `session_id` for later retrieval.

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time
        """

    @abc.abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`"""

    @abc.abstractmethod
    async def delete_all(self) -> None:
        """Delete all data stored within this backend."""

    def generate_session_id(self) -> str:
        """Generate a new session-id, with
        n=[session_id_bytes][ServerSideSessionMiddleware.session_id_bytes]
        random bytes."""
        return secrets.token_hex(self.config.session_id_bytes)

    async def store_in_message(self, message: "Message", connection: ASGIConnection) -> None:
        scope = connection.scope
        headers = MutableHeaders(scope=message)
        scope_session = scope.get("session")

        session_id_source = connection.cookies if self.config.identity_mode == "cookie" else connection.headers
        session_id = session_id_source.get(self.config.key, self.generate_session_id())

        serialised_data = self.serialise_data(scope_session, scope)
        await self.set(session_id=session_id, data=serialised_data)

        cookie_params = self.config.dict(
            exclude_none=True,
            exclude={"secret", "key"} | set(self.config.__fields__) - set(BaseBackendConfig.__fields__),
        )

        if scope_session:
            headers["Set-Cookie"] = Cookie(value=session_id, key=self.config.key, **cookie_params).to_header(header="")
        else:
            headers.append(
                "Set-Cookie",
                Cookie(value="null", key=self.config.key, expires=0, **cookie_params).to_header(header=""),
            )

    async def load_from_connection(self, connection: ASGIConnection) -> Dict[str, Any]:
        session_id = connection.cookies.get(self.config.key)
        if session_id:
            data = await self.get(session_id)
            if isinstance(data, dict):
                return data
            if data is not None:
                return self.deserialise_data(data)
        return {}


B = TypeVar("B", bound=SessionBackend)


class SessionMiddleware(MiddlewareProtocol, Generic[B]):
    __slots__ = ("backend",)

    def __init__(self, app: "ASGIApp", backend: B) -> None:
        self.app = app
        self.backend = backend

    def create_send_wrapper(self, connection: ASGIConnection) -> Callable[["Message"], Awaitable[None]]:
        """
        Creates a wrapper for the ASGI send function, which handles setting the cookies on the outgoing response.
        Args:
            connection: ASGIConnection

        Returns:
            None.
        """

        async def wrapped_send(message: "Message") -> None:
            """A wrapper around the send function, declared in local scope to
            use closure values.

            Args:
                message: An ASGI message.

            Returns:
                None
            """
            if message["type"] != "http.response.start":
                await connection.send(message)
                return

            await self.backend.store_in_message(message, connection)
            await connection.send(message)

        return wrapped_send

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if scope["type"] in self.backend.config.scopes:
            connection = ASGIConnection[Any, Any, Any](scope, receive=receive, send=send)
            scope["session"] = await self.backend.load_from_connection(connection)

            await self.app(scope, receive, self.create_send_wrapper(connection))
        else:
            await self.app(scope, receive, send)
