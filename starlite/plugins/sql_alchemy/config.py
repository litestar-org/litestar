from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import BaseConfig, BaseModel, root_validator, validator
from typing_extensions import Literal

from starlite.config.logging import BaseLoggingConfig, LoggingConfig
from starlite.exceptions import MissingDependencyException
from starlite.types import BeforeMessageSendHookHandler
from starlite.utils import AsyncCallable, default_serializer

from .types import SessionMakerInstanceProtocol, SessionMakerTypeProtocol

try:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
    from sqlalchemy.future import Engine as FutureEngine
    from sqlalchemy.orm import Query, Session, sessionmaker
    from sqlalchemy.pool import Pool

except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

if TYPE_CHECKING:
    from starlite.datastructures.state import State
    from starlite.types import Message, Scope

IsolationLevel = Literal["AUTOCOMMIT", "READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ", "SERIALIZABLE"]

SESSION_SCOPE_KEY = "_sql_alchemy_db_session"
SESSION_TERMINUS_ASGI_EVENTS = {
    "http.response.start",
    "http.disconnect",
    "websocket.disconnect",
    "websocket.close",
}


def serializer(value: Any) -> str:
    """Serializer for JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return dumps(
        value,
        default=default_serializer,
        option=OPT_SERIALIZE_NUMPY,
    ).decode("utf-8")


async def default_before_send_handler(message: "Message", _: "State", scope: "Scope") -> None:
    """
    Handles closing and cleaning up sessions before sending.
    Args:
        message:
        _:
        scope:

    Returns:

    """
    session = cast("Optional[Union[Session, AsyncSession]]", scope.get(SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        if isinstance(session, AsyncSession):
            await session.close()
        else:
            session.close()
        del scope[SESSION_SCOPE_KEY]  # type: ignore


class SQLAlchemySessionConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    autocommit: Optional[bool] = None
    autoflush: Optional[bool] = None
    bind: Optional[Any] = None
    binds: Optional[Any] = None
    enable_baked_queries: Optional[bool] = None
    expire_on_commit: bool = False
    future: Optional[bool] = None
    info: Optional[Dict[str, Any]] = None
    query_cls: Optional[Type[Query]] = None
    twophase: Optional[bool] = None


class SQLAlchemyEngineConfig(BaseModel):
    """This class represents the SQLAlchemy Engine configuration.

    For details see: https://docs.sqlalchemy.org/en/14/core/engines.html
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    connect_args: Optional[Dict[str, Any]] = None
    echo: Optional[bool] = None
    echo_pool: Optional[bool] = None
    enable_from_linting: Optional[bool] = None
    future: bool = True
    hide_parameters: Optional[bool] = None
    isolation_level: Optional[IsolationLevel] = None
    json_deserializer: Callable[[str], Any] = loads
    json_serializer: Callable[[Any], str] = serializer
    label_length: Optional[int] = None
    listeners: Any = None
    logging_level: Optional[Union[int, str]] = None
    logging_name: Optional[str] = None
    max_identifier_length: Optional[int] = None
    max_overflow: Optional[int] = None
    module: Any = None
    paramstyle: Optional[Literal["qmark", "numeric", "named", "format", "pyformat"]] = None
    plugins: Optional[List[str]] = None
    pool: Optional[Pool] = None
    pool_logging_name: Optional[str] = None
    pool_pre_ping: Optional[bool] = None
    pool_recycle: Optional[int] = None
    pool_reset_on_return: Optional[Literal["rollback", "commit"]] = None
    pool_size: Optional[int] = None
    pool_timeout: Optional[int] = None
    pool_use_lifo: Optional[bool] = None
    poolclass: Optional[Type[Pool]] = None
    query_cache_size: Optional[int] = None
    strategy: Optional[str] = None


class SQLAlchemyConfig(BaseModel):
    """This class represents the SQLAlchemy sessionmaker configuration.

    For details see: https://docs.sqlalchemy.org/en/14/orm/session_api.html
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    connection_string: Optional[str] = None
    """Database connection string in one of the formats supported by SQLAlchemy.

    Notes:
    - For async connections, the connection string must include the correct async prefix.
        e.g. 'postgresql+asyncpg://...' instead of 'postgresql://', and for sync connections its the opposite.
    """
    use_async_engine: bool = True
    """
    Dictate whether the engine created is an async connection or not.

    Notes:
    - This option must correlate to the type of 'connection_string'. That is, an async connection string required an
        async connection and vice versa.
    """
    create_async_engine_callable: Callable[[str], AsyncEngine] = create_async_engine
    """
    Callable that creates an 'AsyncEngine' instance or instance of its subclass.
    """
    create_engine_callable: Callable[[str], Union[Engine, FutureEngine]] = create_engine
    """
    Callable that creates an 'Engine' or 'FutureEngine' instance or instance of its subclass.
    """
    dependency_key: str = "db_session"
    """
    Key to use for the dependency injection of database sessions.
    """
    engine_app_state_key: str = "db_engine"
    """
    Key under which to store the SQLAlchemy engine in the application [State][starlite.datastructures.State] instance.
    """
    engine_config: SQLAlchemyEngineConfig = SQLAlchemyEngineConfig()
    """
    Configuration for the SQLAlchemy engine. The configuration options are documented in the SQLAlchemy documentation.
    """
    set_json_serializers: bool = True
    """
    A boolean flag dictating whether to set 'orjson' based serializer/deserializer functions.

    Notes:
    - Some databases or some versions of some databases do not have a JSON column type. E.g. some older versions of
        SQLite for example. In this case this flag should be false or an error will be raised by SQLAlchemy.
    """
    session_class: Optional[Union[Type[Session], Type[AsyncSession]]] = None
    """
    The session class to use. If not set, the session class will default to 'sqlalchemy.orm.Session' for sync
        connections and 'sqlalchemy.ext.asyncio.AsyncSession' for async ones.
    """
    session_config: SQLAlchemySessionConfig = SQLAlchemySessionConfig()
    """
    Configuration options for the 'sessionmaker'. The configuration options are documented in the
        SQLAlchemy documentation.
    """
    session_maker_class: Type[SessionMakerTypeProtocol] = sessionmaker
    """
    Sessionmaker class to use.
    """
    session_maker_app_state_key: str = "session_maker_class"
    """
    Key under which to store the SQLAlchemy 'sessionmaker' in the application [State][starlite.datastructures.State] instance.
    """
    session_maker_instance: Optional[SessionMakerInstanceProtocol] = None
    """
    Optional sessionmaker to use. If set, the plugin will use the provided instance rather than instantiate a sessionmaker.
    """
    engine_instance: Optional[Union[Engine, FutureEngine, AsyncEngine]] = None
    """
    Optional engine to use. If set, the plugin will use the provided instance rather than instantiate an engine.
    """
    before_send_handler: BeforeMessageSendHookHandler = default_before_send_handler
    """
    Handler to call before the ASGI message is sent. The handler should handle closing the session stored in the ASGI
    scope, if its still open, and committing and uncommitted data.
    """

    @validator("before_send_handler", always=True)
    def validate_before_send_handler(  # pylint: disable=no-self-argument
        cls, value: BeforeMessageSendHookHandler
    ) -> Any:
        """

        Args:
            value: A before send handler callable.

        Returns:
            The handler wrapped in AsyncCallable.
        """
        return AsyncCallable(value)  # type: ignore[arg-type]

    @root_validator
    def check_connection_string_or_engine_instance(  # pylint: disable=no-self-argument
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Either `connection_string` or `engine_instance` must be specified,
        and not both.

        Args:
            values: Field values, after validation.

        Returns:
            Field values.
        """
        connection_string = values.get("connection_string")
        engine_instance = values.get("engine_instance")

        if connection_string is None and engine_instance is None:
            raise ValueError("One of 'connection_string' or 'engine_instance' must be provided.")

        if connection_string is not None and engine_instance is not None:
            raise ValueError("Only one of 'connection_string' or 'engine_instance' can be provided.")

        return values

    @property
    def engine_config_dict(self) -> Dict[str, Any]:
        """

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy 'create_engine' function.
        """
        engine_excluded_fields: Set[str] = {"future", "logging_level"} if self.use_async_engine else {"logging_level"}

        if not self.set_json_serializers:
            engine_excluded_fields.update({"json_deserializer", "json_serializer"})

        return self.engine_config.dict(exclude_none=True, exclude=engine_excluded_fields)

    @property
    def engine(self) -> Union["Engine", "FutureEngine", "AsyncEngine"]:
        """

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
        return cast("Union[Engine, FutureEngine, AsyncEngine]", self.engine_instance)

    @property
    def session_maker(self) -> sessionmaker:
        """

        Returns:
            Getter that returns the session_maker instance used by the plugin.
        """
        if not self.session_maker_instance:
            session_maker_kwargs = self.session_config.dict(
                exclude_none=True, exclude={"future"} if self.use_async_engine else set()
            )
            session_class = self.session_class or (AsyncSession if self.use_async_engine else Session)
            self.session_maker_instance = self.session_maker_class(
                self.engine, class_=session_class, **session_maker_kwargs
            )
        return cast("sessionmaker", self.session_maker_instance)

    def create_db_session_dependency(self, state: "State", scope: "Scope") -> Union[Session, AsyncSession]:
        """

        Args:
            state: The 'application.state' instance.
            scope: The current connection's scope.

        Returns:
            A session instance T.
        """
        session = scope.get(SESSION_SCOPE_KEY)
        if not session:
            session_maker = cast("sessionmaker", state[self.session_maker_app_state_key])
            session = scope[SESSION_SCOPE_KEY] = session_maker()  # type: ignore
        return cast("Union[Session, AsyncSession]", session)

    def update_app_state(self, state: "State") -> None:
        """Create a DB engine and stores it in the application state.

        Args:
            state: The 'application.state' instance.

        Returns:
            None
        """

        state[self.engine_app_state_key] = self.engine
        state[self.session_maker_app_state_key] = self.session_maker

    async def on_shutdown(self, state: "State") -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            state: The 'application.state' instance.

        Returns:
            None
        """
        engine = cast("Union[Engine, AsyncEngine]", state[self.engine_app_state_key])
        if isinstance(engine, AsyncEngine):
            await engine.dispose()
        else:
            engine.dispose()
        del state[self.engine_app_state_key]

    def config_sql_alchemy_logging(self, logging_config: Optional[BaseLoggingConfig]) -> None:
        """Adds the SQLAlchemy loggers to the logging config. Currently working
        only with [LoggingConfig][starlite.config.logging.LoggingConfig].

        Args:
            logging_config: Logging config.

        Returns:
            None.
        """
        if isinstance(logging_config, LoggingConfig):
            logger_settings = {
                "level": self.engine_config.logging_level or "WARNING",
                "handlers": logging_config.loggers["starlite"]["handlers"],
            }
            for logger in (
                "sqlalchemy",
                self.engine_config.logging_name or "sqlalchemy.engine",
                self.engine_config.pool_logging_name or "sqlalchemy.pool",
            ):
                if logger not in logging_config.loggers:
                    logging_config.loggers[logger] = logger_settings
