from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from litestar.exceptions import ImproperlyConfiguredException, MissingDependencyException
from litestar.logging.config import BaseLoggingConfig, LoggingConfig
from litestar.serialization import decode_json, encode_json
from litestar.utils import AsyncCallable

try:
    import sqlalchemy  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("sqlalchemy") from e

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Query, Session, sessionmaker

__all__ = ("SQLAlchemyConfig", "SQLAlchemyEngineConfig", "SQLAlchemySessionConfig")


if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.future import Engine as FutureEngine
    from sqlalchemy.pool import Pool

    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, Message, Scope

    from .types import SessionMakerInstanceProtocol, SessionMakerTypeProtocol

IsolationLevel = Literal["AUTOCOMMIT", "READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ", "SERIALIZABLE"]

SESSION_SCOPE_KEY = "_sql_alchemy_db_session"
SESSION_TERMINUS_ASGI_EVENTS = {"http.response.start", "http.disconnect", "websocket.disconnect", "websocket.close"}


def serializer(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return encode_json(value).decode("utf-8")


async def default_before_send_handler(message: "Message", _: "State", scope: "Scope") -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        _: A ``State`` (not used)
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("Session | AsyncSession | None", scope.get(SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        if isinstance(session, AsyncSession):
            await session.close()
        else:
            session.close()
        del scope[SESSION_SCOPE_KEY]  # type: ignore


@dataclass
class SQLAlchemySessionConfig:
    """Configuration for a SQLAlchemy-Session."""

    autocommit: bool | None = field(default=None)
    autoflush: bool | None = field(default=None)
    bind: Any | None = field(default=None)
    binds: Any | None = field(default=None)
    enable_baked_queries: bool | None = field(default=None)
    expire_on_commit: bool = field(default=False)
    future: bool | None = field(default=None)
    info: dict[str, Any] | None = field(default=None)
    query_cls: type[Query] | None = field(default=None)
    twophase: bool | None = field(default=None)


@dataclass
class SQLAlchemyEngineConfig:
    """Configuration for SQLAlchemy's :class`Engine <sqlalchemy.engine.Engine>`.

    For details see: https://docs.sqlalchemy.org/en/14/core/engines.html
    """

    connect_args: dict[str, Any] | None = field(default=None)
    echo: bool | None = field(default=None)
    echo_pool: bool | None = field(default=None)
    enable_from_linting: bool | None = field(default=None)
    future: bool = field(default=True)
    hide_parameters: bool | None = field(default=None)
    isolation_level: IsolationLevel | None = field(default=None)
    json_deserializer: Callable[[str], Any] = field(default=decode_json)
    json_serializer: Callable[[Any], str] = field(default=serializer)
    label_length: int | None = field(default=None)
    listeners: Any = field(default=None)
    logging_level: int | str | None = field(default=None)
    logging_name: str | None = field(default=None)
    max_identifier_length: int | None = field(default=None)
    max_overflow: int | None = field(default=None)
    module: Any = field(default=None)
    paramstyle: Literal["qmark", "numeric", "named", "format", "pyformat"] | None = field(default=None)
    plugins: list[str] | None = field(default=None)
    pool: Pool | None = field(default=None)
    pool_logging_name: str | None = field(default=None)
    pool_pre_ping: bool | None = field(default=None)
    pool_recycle: int | None = field(default=None)
    pool_reset_on_return: Literal["rollback", "commit"] | None = field(default=None)
    pool_size: int | None = field(default=None)
    pool_timeout: int | None = field(default=None)
    pool_use_lifo: bool | None = field(default=None)
    poolclass: type[Pool] | None = field(default=None)
    query_cache_size: int | None = field(default=None)
    strategy: str | None = field(default=None)


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
    use_async_engine: bool = field(default=True)
    """Dictate whether the engine created is an async connection or not.

    Notes:
        - This option must correlate to the type of ``connection_string``. That is, an async connection string required an
          async connection and vice versa.

    """
    create_async_engine_callable: Callable[[str], AsyncEngine] = field(default=create_async_engine)
    """Callable that creates an :class:`AsyncEngine <sqlalchemy.ext.asyncio.AsyncEngine>` instance or instance of its
    subclass.
    """
    create_engine_callable: Callable[[str], Engine | FutureEngine] = field(default=create_engine)
    """Callable that creates an :class:`Engine <sqlalchemy.engine.Engine>` or ``FutureEngine`` instance or instance of its
    subclass."""
    dependency_key: str = field(default="db_session")
    """Key to use for the dependency injection of database sessions."""
    engine_app_state_key: str = field(default="db_engine")
    """Key under which to store the SQLAlchemy engine in the application :class:`State <.datastructures.State>`
    instance.
    """
    engine_config: SQLAlchemyEngineConfig = field(default_factory=SQLAlchemyEngineConfig)
    """Configuration for the SQLAlchemy engine.

    The configuration options are documented in the SQLAlchemy documentation.
    """
    set_json_serializers: bool = field(default=True)
    """A boolean flag dictating whether to set ``msgspec`` based serializer/deserializer functions.

    Notes:
        - Some databases or some versions of some databases do not have a JSON column type. E.g. some older versions of
          SQLite for example. In this case this flag should be false or an error will be raised by SQLAlchemy.

    """
    session_class: type[Session] | type[AsyncSession] | None = field(default=None)
    """The session class to use.

    If not set, the session class will default to :class:`sqlalchemy.orm.Session` for sync connections and
    :class:`sqlalchemy.ext.asyncio.AsyncSession` for async ones.
    """
    session_config: SQLAlchemySessionConfig = field(default_factory=SQLAlchemySessionConfig)
    """Configuration options for the ``sessionmaker``.

    The configuration options are documented in the SQLAlchemy documentation.
    """
    session_maker_class: type[SessionMakerTypeProtocol] = field(default=sessionmaker)
    """Sessionmaker class to use."""
    session_maker_app_state_key: str = field(default="session_maker_class")
    """Key under which to store the SQLAlchemy ``sessionmaker`` in the application
    :class:`State <.datastructures.State>` instance.
    """
    session_maker_instance: SessionMakerInstanceProtocol | None = field(default=None)
    """Optional sessionmaker to use.

    If set, the plugin will use the provided instance rather than instantiate a sessionmaker.
    """
    engine_instance: Engine | FutureEngine | AsyncEngine | None = field(default=None)
    """Optional engine to use.

    If set, the plugin will use the provided instance rather than instantiate an engine.
    """
    before_send_handler: BeforeMessageSendHookHandler = field(default=default_before_send_handler)
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if its still open, and committing and
    uncommitted data.
    """

    def __post_init__(self) -> None:
        if self.connection_string is None and self.engine_instance is None:
            raise ImproperlyConfiguredException("One of 'connection_string' or 'engine_instance' must be provided.")

        if self.connection_string is not None and self.engine_instance is not None:
            raise ImproperlyConfiguredException("Only one of 'connection_string' or 'engine_instance' can be provided.")

        self.before_send_handler = AsyncCallable(self.before_send_handler)  # type: ignore

    @property
    def engine_config_dict(self) -> dict[str, Any]:
        """Return the engine configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy ``create_engine`` function.
        """
        engine_excluded_fields: set[str] = {"future", "logging_level"} if self.use_async_engine else {"logging_level"}

        if not self.set_json_serializers:
            engine_excluded_fields.update({"json_deserializer", "json_serializer"})

        return {
            k: v for k, v in asdict(self.engine_config).items() if v is not None and k not in engine_excluded_fields
        }

    @property
    def engine(self) -> Engine | FutureEngine | AsyncEngine:
        """Return an engine. If none exists yet, create one.

        Returns:
            Getter that returns the engine instance used by the plugin.
        """
        if not self.engine_instance:
            create_engine_callable = (
                self.create_async_engine_callable if self.use_async_engine else self.create_engine_callable
            )
            self.engine_instance = create_engine_callable(
                self.connection_string, **self.engine_config_dict  # type:ignore[arg-type]
            )
        return cast("Engine | FutureEngine | AsyncEngine", self.engine_instance)

    @property
    def session_maker(self) -> sessionmaker:
        """Get a sessionmaker. If none exists yet, create one.

        Returns:
            Getter that returns the session_maker instance used by the plugin.
        """
        if not self.session_maker_instance:
            session_maker_kwargs = {
                k: v
                for k, v in asdict(self.session_config).items()
                if v is not None and ((self.use_async_engine and k != "future") or not self.use_async_engine)
            }
            session_class = self.session_class or (AsyncSession if self.use_async_engine else Session)
            self.session_maker_instance = self.session_maker_class(
                self.engine, class_=session_class, **session_maker_kwargs
            )
        return cast("sessionmaker", self.session_maker_instance)

    def create_db_session_dependency(self, state: State, scope: Scope) -> Union[Session, AsyncSession]:  # noqa: F821
        """Create a session instance.

        Args:
            state: The ``Litestar.state`` instance.
            scope: The current connection's scope.

        Returns:
            A session instance T.
        """
        session = scope.get(SESSION_SCOPE_KEY)
        if not session:
            session_maker = cast("sessionmaker", state[self.session_maker_app_state_key])
            session = scope[SESSION_SCOPE_KEY] = session_maker()  # type: ignore
        return cast("Session | AsyncSession", session)

    def update_app_state(self, state: State) -> None:
        """Create a DB engine and stores it in the application state.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            None
        """

        state[self.engine_app_state_key] = self.engine
        state[self.session_maker_app_state_key] = self.session_maker

    async def on_shutdown(self, state: State) -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            None
        """
        engine = cast("Engine | AsyncEngine", state[self.engine_app_state_key])
        if isinstance(engine, AsyncEngine):
            await engine.dispose()
        else:
            engine.dispose()
        del state[self.engine_app_state_key]

    def config_sql_alchemy_logging(self, logging_config: BaseLoggingConfig | None) -> None:
        """Add the SQLAlchemy loggers to the logging config.

        Notes:
            - Currently only works with :class:`LoggingConfig <.logging.config.LoggingConfig>`.

        Args:
            logging_config: Logging config.

        Returns:
            None.
        """
        if isinstance(logging_config, LoggingConfig):
            logger_settings = {
                "level": self.engine_config.logging_level or "WARNING",
                "handlers": logging_config.loggers["litestar"]["handlers"],
            }
            for logger in (
                "sqlalchemy",
                self.engine_config.logging_name or "sqlalchemy.engine",
                self.engine_config.pool_logging_name or "sqlalchemy.pool",
            ):
                if logger not in logging_config.loggers:
                    logging_config.loggers[logger] = logger_settings
