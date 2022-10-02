from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import BaseConfig, BaseModel
from pydantic.generics import GenericModel
from sqlalchemy.orm import Query, Session
from typing_extensions import Literal

from starlite.config.logging import BaseLoggingConfig, LoggingConfig
from starlite.exceptions import MissingDependencyException
from starlite.utils import default_serializer

try:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
    from sqlalchemy.future import Engine as FutureEngine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import Pool

except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

if TYPE_CHECKING:
    from starlite.datastructures import State
    from starlite.types import Message, Scope

T = TypeVar("T", Session, AsyncSession)

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


class SQLAlchemySessionConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    bind: Optional[Any] = None
    autoflush: Optional[bool] = None
    future: Optional[bool] = None
    autocommit: Optional[bool] = None
    expire_on_commit: bool = False
    twophase: Optional[bool] = None
    binds: Optional[Any] = None
    enable_baked_queries: Optional[bool] = None
    info: Optional[Dict[str, Any]] = None
    query_cls: Optional[Type[Query]] = None


class SQLAlchemyEngineConfig(BaseModel):
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


class SQLAlchemyConfig(GenericModel, Generic[T]):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    connection_string: str
    create_engine_callable: Callable[[str], Union[Engine, FutureEngine]] = create_engine
    create_async_engine_callable: Callable[[str], AsyncEngine] = create_async_engine
    create_async_engine: bool = True
    session_class: Optional[Type[T]] = None
    session_maker_app_state_key: str = "session_maker"
    engine_app_state_key: str = "db_engine"
    dependency_key: str = "db_session"
    session_config: SQLAlchemySessionConfig = SQLAlchemySessionConfig()
    engine_config: SQLAlchemyEngineConfig = SQLAlchemyEngineConfig()
    engine_supports_json: bool = True

    @property
    def engine_config_dict(self) -> Dict[str, Any]:
        """

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy 'create_engine' function.
        """
        engine_excluded_fields: Set[str] = (
            {"future", "logging_level"} if self.create_async_engine else {"logging_level"}
        )

        if not self.engine_supports_json:
            engine_excluded_fields.update({"json_deserializer", "json_serializer"})

        return self.engine_config.dict(exclude_none=True, exclude=engine_excluded_fields)

    def create_db_session_dependency(self, state: "State", scope: "Scope") -> T:
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
        return cast("T", session)

    def update_app_state(self, state: "State") -> None:
        """Create a DB engine and stores it in the application state.

        Args:
            state: The 'application.state' instance.

        Returns:
            None
        """
        create_engine_callable = (
            self.create_async_engine_callable if self.create_async_engine else self.create_engine_callable
        )
        session_maker_kwargs = self.session_config.dict(
            exclude_none=True, exclude={"future"} if self.create_async_engine else set()
        )
        session_class = self.session_class or (AsyncSession if self.create_async_engine else Session)
        engine = state[self.engine_app_state_key] = create_engine_callable(
            self.connection_string, **self.engine_config_dict
        )
        state[self.session_maker_app_state_key] = sessionmaker(engine, class_=session_class, **session_maker_kwargs)

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

    @staticmethod
    async def before_send_handler(message: "Message", _: "State", scope: "Scope") -> None:
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

    def config_sql_alchemy_logging(self, logging_config: Optional[BaseLoggingConfig]) -> None:
        """Adds the SQLAlchemy loggers to the logging config. Currently working
        only with [LoggingConfig][starlite.config.logging.LoggingConfig].

        Args:
            logging_config: Logging config.

        Returns:
            None.
        """
        if isinstance(logging_config, LoggingConfig):
            engine_logger = self.engine_config.logging_name or "sqlalchemy.engine"
            pool_logger = self.engine_config.pool_logging_name or "sqlalchemy.pool"
            for logger in ("sqlalchemy", engine_logger, pool_logger):
                if logger not in logging_config.loggers:
                    logging_config.loggers[logger] = {
                        "level": self.engine_config.logging_level or "WARNING",
                        "handlers": logging_config.loggers["starlite"]["handlers"],
                    }
