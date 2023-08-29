from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, cast

from asyncpg import Record
from asyncpg import create_pool as asyncpg_create_pool
from asyncpg.connection import Connection
from asyncpg.pool import Pool, PoolConnectionProxy

from litestar.constants import HTTP_DISCONNECT, HTTP_RESPONSE_START, WEBSOCKET_CLOSE, WEBSOCKET_DISCONNECT
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import decode_json, encode_json
from litestar.types import Empty
from litestar.utils import delete_litestar_scope_state, get_litestar_scope_state, set_litestar_scope_state
from litestar.utils.dataclass import simple_asdict

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import AsyncGenerator, Callable, Coroutine
    from typing import Any

    from litestar import Litestar
    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, EmptyType, Message, Scope


SESSION_SCOPE_KEY = "_asyncpg_db_connection"
SESSION_TERMINUS_ASGI_EVENTS = {HTTP_RESPONSE_START, HTTP_DISCONNECT, WEBSOCKET_DISCONNECT, WEBSOCKET_CLOSE}
T = TypeVar("T")


class SlotsBase:
    __slots__ = ("_config",)


async def default_before_send_handler(message: Message, scope: Scope) -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("Connection | PoolConnectionProxy | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
    if session is not None:
        delete_litestar_scope_state(scope, SESSION_SCOPE_KEY)


def serializer(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return encode_json(value).decode("utf-8")


@dataclass
class PoolConfig:
    """Configuration for Asyncpg's :class:`Pool <asyncpg.pool.Pool>`.

    For details see: https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools
    """

    dsn: str
    """Connection arguments specified using as a single string in the following format: ``postgres://user:pass@host:port/database?option=value``
    """
    connect_kwargs: dict[Any, Any] | None | EmptyType = Empty
    """A dictionary of arguments which will be passed directly to the ``connect()`` method as keyword arguments.
    """
    connection_class: type[Connection] | None | EmptyType = Empty
    """The class to use for connections. Must be a subclass of Connection
    """
    record_class: type[Record] | EmptyType = Empty
    """If specified, the class to use for records returned by queries on the connections in this pool. Must be a subclass of Record."""

    min_size: int | EmptyType = Empty
    """The number of connections to keep open inside the connection pool."""
    max_size: int | EmptyType = Empty
    """The number of connections to allow in connection pool “overflow”, that is connections that can be opened above
    and beyond the pool_size setting, which defaults to 10."""

    max_queries: int | EmptyType = Empty
    """Number of queries after a connection is closed and replaced with a new connection.
    """
    max_inactive_connection_lifetime: float | EmptyType = Empty
    """Number of seconds after which inactive connections in the pool will be closed. Pass 0 to disable this mechanism."""

    setup: Coroutine[None, type[Connection], Any] | EmptyType = Empty
    """A coroutine to prepare a connection right before it is returned from Pool.acquire(). An example use case would be to automatically set up notifications listeners for all connections of a pool."""
    init: Coroutine[None, type[Connection], Any] | EmptyType = Empty
    """A coroutine to prepare a connection right before it is returned from Pool.acquire(). An example use case would be to automatically set up notifications listeners for all connections of a pool."""

    loop: AbstractEventLoop | EmptyType = Empty
    """An asyncio event loop instance. If None, the default event loop will be used."""


@dataclass
class AsyncpgConfig:
    """Asyncpg Configuration."""

    pool_config: PoolConfig | None = None
    """Asyncpg Pool configuration"""
    pool_app_state_key: str = "db_pool"
    """Key under which to store the asyncpg pool in the application :class:`State <.datastructures.State>`
    instance.
    """
    before_send_handler: BeforeMessageSendHookHandler = default_before_send_handler
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if it's still open, and committing and
    uncommitted data.
    """
    json_deserializer: Callable[[str], Any] = decode_json
    """For dialects that support the :class:`JSON <sqlalchemy.types.JSON>` datatype, this is a Python callable that will
    convert a JSON string to a Python object. By default, this is set to Litestar's
    :attr:`decode_json() <.serialization.decode_json>` function."""
    json_serializer: Callable[[Any], str] = serializer
    """For dialects that support the JSON datatype, this is a Python callable that will render a given object as JSON.
    By default, Litestar's :attr:`encode_json() <.serialization.encode_json>` is used."""
    pool_instance: Pool | None = None
    """Optional pool to use.

    If set, the plugin will use the provided pool rather than instantiate one.
    """

    @property
    def pool_config_dict(self) -> dict[str, Any]:
        """Return the pool configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the Asyncpg :func:`create_pool <asyncpg.pool.create_pool>`
            function.
        """
        if self.pool_config:
            return simple_asdict(self.pool_config, exclude_empty=True, convert_nested=False)
        raise ImproperlyConfiguredException("'pool_config' methods can not be used when a 'pool_instance' is provided.")

    @property
    def signature_namespace(self) -> dict[str, Any]:
        """Return the plugin's signature namespace.

        Returns:
            A string keyed dict of names to be added to the namespace for signature forward reference resolution.
        """
        return {"Connection": Connection, "Pool": Pool, "PoolConnectionProxy": PoolConnectionProxy}

    async def create_pool(self) -> Pool:
        """Return a pool. If none exists yet, create one.

        Returns:
            Getter that returns the pool instance used by the plugin.
        """
        if self.pool_instance is not None:
            return self.pool_instance

        if self.pool_config is None:
            raise ImproperlyConfiguredException("One of 'pool_config' or 'pool_instance' must be provided.")

        pool_config = self.pool_config_dict
        self.pool_instance = await asyncpg_create_pool(**pool_config)
        if self.pool_instance is None:
            raise ImproperlyConfiguredException(
                "Could not configure the 'pool_instance'. Please check your configuration."
            )
        return self.pool_instance

    @asynccontextmanager
    async def lifespan(
        self,
        app: Litestar,
    ) -> AsyncGenerator[None, None]:
        db_pool = await self.create_pool()
        app.state.update({self.pool_app_state_key: db_pool})
        try:
            yield
        finally:
            db_pool.terminate()
            await db_pool.close()

    def provide_pool(self, state: State) -> Pool:
        """Create a pool instance.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            A Pool instance.
        """
        return cast("Pool", state.get(self.pool_app_state_key))

    async def provide_connection(
        self, state: State, scope: Scope
    ) -> AsyncGenerator[Connection | PoolConnectionProxy, None]:
        """Create a connection instance.

        Args:
            state: The ``Litestar.state`` instance.
            scope: The current connection's scope.

        Returns:
            A connection instance.
        """
        connection = cast("Connection | PoolConnectionProxy | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
        if connection is None:
            pool = cast("Pool", state.get(self.pool_app_state_key))

            async with pool.acquire() as connection:
                set_litestar_scope_state(scope, SESSION_SCOPE_KEY, connection)
                yield connection
