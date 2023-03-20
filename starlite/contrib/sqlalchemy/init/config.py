from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Callable, Literal, cast

from starlite.exceptions import ImproperlyConfiguredException, MissingDependencyException
from starlite.serialization import decode_json, encode_json
from starlite.types import Empty
from starlite.utils import (
    AsyncCallable,
    delete_starlite_scope_state,
    get_starlite_scope_state,
    set_starlite_scope_state,
)

try:
    import sqlalchemy  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

__all__ = ("SQLAlchemyConfig", "SQLAlchemyEngineConfig", "SQLAlchemySessionConfig")


if TYPE_CHECKING:
    from typing import Any, Mapping

    from sqlalchemy.engine.interfaces import IsolationLevel
    from sqlalchemy.ext.asyncio import AsyncConnection
    from sqlalchemy.orm import Mapper, Query, Session
    from sqlalchemy.orm.session import JoinTransactionMode
    from sqlalchemy.pool import Pool
    from sqlalchemy.sql import TableClause
    from typing_extensions import TypeAlias

    from starlite.datastructures.state import State
    from starlite.types import BeforeMessageSendHookHandler, EmptyType, Message, Scope

_EchoFlagType: TypeAlias = "None | bool | Literal['debug']"
_ParamStyle = Literal["qmark", "numeric", "named", "format", "pyformat", "numeric_dollar"]

SESSION_SCOPE_KEY = "_sqlalchemy_db_session"
SESSION_TERMINUS_ASGI_EVENTS = {"http.response.start", "http.disconnect", "websocket.disconnect", "websocket.close"}


def serializer(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return encode_json(value).decode("utf-8")


async def default_before_send_handler(message: Message, _: State, scope: Scope) -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        _: A ``State`` (not used)
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("AsyncSession | None", get_starlite_scope_state(scope, SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        await session.close()
        delete_starlite_scope_state(scope, SESSION_SCOPE_KEY)


def asdict_filter_empty(obj: Any) -> dict[str, Any]:
    return {k: v for k, v in asdict(obj).items() if v is not Empty}


@dataclass
class SQLAlchemySessionConfig:
    """SQLAlchemy async session config."""

    autobegin: bool | EmptyType = Empty
    autoflush: bool | EmptyType = Empty
    bind: AsyncEngine | AsyncConnection | None | EmptyType = Empty
    binds: dict[type[Any] | Mapper[Any] | TableClause | str, AsyncEngine | AsyncConnection] | None | EmptyType = Empty
    class_: type[AsyncSession] | EmptyType = Empty
    enable_baked_queries: bool | EmptyType = Empty
    expire_on_commit: bool | EmptyType = Empty
    info: dict[str, Any] | None | EmptyType = Empty
    join_transaction_mode: JoinTransactionMode | EmptyType = Empty
    query_cls: type[Query] | None | EmptyType = Empty
    sync_session_class: type[Session] | None | EmptyType = Empty
    twophase: bool | EmptyType = Empty


@dataclass
class SQLAlchemyEngineConfig:
    """Configuration for SQLAlchemy's :class`Engine <sqlalchemy.engine.Engine>`.

    For details see: https://docs.sqlalchemy.org/en/20/core/engines.html
    """

    connect_args: dict[Any, Any] | EmptyType = Empty
    echo: _EchoFlagType | EmptyType = Empty
    echo_pool: _EchoFlagType | EmptyType = Empty
    enable_from_linting: bool | EmptyType = Empty
    execution_options: Mapping[str, Any] | EmptyType = Empty
    hide_parameters: bool | EmptyType = Empty
    insertmanyvalues_page_size: int | EmptyType = Empty
    isolation_level: IsolationLevel | EmptyType = Empty
    json_deserializer: Callable[[str], Any] = decode_json
    json_serializer: Callable[[Any], str] = serializer
    label_length: int | None | EmptyType = Empty
    logging_name: str | EmptyType = Empty
    max_identifier_length: int | None | EmptyType = Empty
    max_overflow: int | EmptyType = Empty
    module: Any | None | EmptyType = Empty
    paramstyle: _ParamStyle | None | EmptyType = Empty
    pool: Pool | None | EmptyType = Empty
    poolclass: type[Pool] | None | EmptyType = Empty
    pool_logging_name: str | EmptyType = Empty
    pool_pre_ping: bool | EmptyType = Empty
    pool_size: int | EmptyType = Empty
    pool_recycle: int | EmptyType = Empty
    pool_reset_on_return: Literal["rollback", "commit"] | EmptyType = Empty
    pool_timeout: int | EmptyType = Empty
    pool_use_lifo: bool | EmptyType = Empty
    plugins: list[str] | EmptyType = Empty
    query_cache_size: int | EmptyType = Empty
    use_insertmanyvalues: bool | EmptyType = Empty


@dataclass
class SQLAlchemyConfig:
    """Configuration for SQLAlchemy's :class:`sessionmaker <sqlalchemy.orm.sessionmaker>`.

    For details see: https://docs.sqlalchemy.org/en/14/orm/session_api.html
    """

    connection_string: str | None = field(default=None)
    """Database connection string in one of the formats supported by SQLAlchemy.

    Notes:
        - For async connections, the connection string must include the correct async prefix.
          e.g. ``'postgresql+asyncpg://...'`` instead of ``'postgresql://'``, and for sync connections its the opposite.

    """
    create_engine_callable: Callable[[str], AsyncEngine] = create_async_engine
    """Callable that creates an :class:`AsyncEngine <sqlalchemy.ext.asyncio.AsyncEngine>` instance or instance of its
    subclass.
    """
    dependency_key: str = "db_session"
    """Key to use for the dependency injection of database sessions."""
    engine_app_state_key: str = "db_engine"
    """Key under which to store the SQLAlchemy engine in the application :class:`State <.datastructures.State>`
    instance.
    """
    engine_config: SQLAlchemyEngineConfig = field(default_factory=SQLAlchemyEngineConfig)
    """Configuration for the SQLAlchemy engine.

    The configuration options are documented in the SQLAlchemy documentation.
    """
    session_config: SQLAlchemySessionConfig = field(default_factory=SQLAlchemySessionConfig)
    """Configuration options for the ``sessionmaker``.

    The configuration options are documented in the SQLAlchemy documentation.
    """
    session_maker_class: type[async_sessionmaker] = async_sessionmaker
    """Sessionmaker class to use."""
    session_maker_app_state_key: str = "session_maker_class"
    """Key under which to store the SQLAlchemy ``sessionmaker`` in the application
    :class:`State <.datastructures.State>` instance.
    """
    session_maker_instance: async_sessionmaker | None = None
    """Optional sessionmaker to use.

    If set, the plugin will use the provided instance rather than instantiate a sessionmaker.
    """
    engine_instance: AsyncEngine | None = None
    """Optional engine to use.

    If set, the plugin will use the provided instance rather than instantiate an engine.
    """
    before_send_handler: BeforeMessageSendHookHandler = default_before_send_handler
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if its still open, and committing and
    uncommitted data.
    """

    def __post_init__(self) -> None:
        if self.connection_string is not None and self.engine_instance is not None:
            raise ImproperlyConfiguredException("Only one of 'connection_string' or 'engine_instance' can be provided.")

    @property
    def engine_config_dict(self) -> dict[str, Any]:
        """Return the engine configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy ``create_engine`` function.
        """
        return asdict_filter_empty(self.engine_config)

    def create_engine(self) -> AsyncEngine:
        """Return an engine. If none exists yet, create one.

        Returns:
            Getter that returns the engine instance used by the plugin.
        """
        if self.engine_instance:
            return self.engine_instance

        if self.connection_string is None:
            raise ImproperlyConfiguredException("One of 'connection_string' or 'engine_instance' must be provided.")

        engine_config = self.engine_config_dict
        try:
            return self.create_engine_callable(self.connection_string, **self.engine_config_dict)
        except ValueError:
            # likely due to a dialect that doesn't support json type
            del engine_config["json_deserializer"]
            del engine_config["json_serializer"]
            return self.create_engine_callable(self.connection_string, **self.engine_config_dict)

    def create_session_maker(self) -> async_sessionmaker:
        """Get a session maker. If none exists yet, create one.

        Returns:
            Session factory used by the plugin.
        """
        if self.session_maker_instance:
            return self.session_maker_instance

        session_kws = asdict_filter_empty(self.session_config)
        if session_kws.get("bind") is None:
            session_kws["bind"] = self.create_engine()
        return self.session_maker_class(**session_kws)

    def create_db_session_dependency(self, state: State, scope: Scope) -> AsyncSession:
        """Create a session instance.

        Args:
            state: The ``Starlite.state`` instance.
            scope: The current connection's scope.

        Returns:
            A session instance.
        """
        session = cast("AsyncSession | None", get_starlite_scope_state(scope, SESSION_SCOPE_KEY))
        if session is None:
            session_maker = cast("async_sessionmaker", state[self.session_maker_app_state_key])
            session = session_maker()
            set_starlite_scope_state(scope, SESSION_SCOPE_KEY, session)
        return session

    def app_state(self) -> dict[str, Any]:
        """Key/value pairs to be stored in application state."""
        return {
            self.engine_app_state_key: self.create_engine(),
            self.session_maker_app_state_key: self.create_session_maker(),
        }

    async def on_shutdown(self, state: State) -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            state: The ``Starlite.state`` instance.

        Returns:
            None
        """
        engine = cast("AsyncEngine", state.pop(self.engine_app_state_key))
        await engine.dispose()
