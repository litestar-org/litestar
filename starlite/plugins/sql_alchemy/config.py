from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import BaseConfig, BaseModel
from sqlalchemy.orm import Query, Session
from typing_extensions import Literal

from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import DefineMiddleware
from starlite.utils import default_serializer

from ... import BaseLoggingConfig, LoggingConfig

try:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
    from sqlalchemy.future import Engine as FutureEngine
    from sqlalchemy.pool import Pool

    from .middleware import SQLAlchemySessionMiddleware
except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

if TYPE_CHECKING:
    from starlite.datastructures import State

IsolationLevel = Literal["AUTOCOMMIT", "READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ", "SERIALIZABLE"]


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
    expire_on_commit: bool = True
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


class SQLAlchemyConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    connection_string: str
    middleware_class: Type[SQLAlchemySessionMiddleware] = SQLAlchemySessionMiddleware
    create_engine_callable: Callable[[str, Any], Union[Engine, FutureEngine]] = create_engine
    create_async_engine_callable: Callable[[str, Any], AsyncEngine] = create_async_engine
    create_async_engine: bool = True
    session_class: Optional[Union[Type[Session], Type[AsyncSession]]] = None
    session_scope_key: str = "db_session"
    engine_app_state_key: str = "db_engine"
    session_config: SQLAlchemySessionConfig = SQLAlchemySessionConfig()
    engine_config: SQLAlchemyEngineConfig = SQLAlchemyEngineConfig()

    @property
    def middleware(self) -> DefineMiddleware:
        """
        Returns:
            An instance of DefineMiddleware populated by 'self.middleware_class' and config args for the session.

        """
        if not self.session_class:
            session_class = AsyncSession if self.create_async_engine else Session
        else:
            session_class = self.session_class
        return DefineMiddleware(
            self.middleware_class,
            engine_app_state_key=self.engine_app_state_key,
            session_class=session_class,
            **self.session_config.dict(exclude_none=True)
        )

    def create_engine(self, state: "State") -> None:
        """Create a DB engine and stores it in the application state.

        Args:
            state: The 'application.state' instance.

        Returns:
            None
        """
        engine_config: Dict[str, Any] = self.engine_config.dict(exclude_none=True, exclude={"future"})
        state[self.engine_app_state_key] = (
            self.create_async_engine_callable(self.connection_string, **engine_config)  # type: ignore
            if self.create_async_engine
            else self.create_engine_callable(self.connection_string, future=self.engine_config.future, **engine_config)  # type: ignore
        )

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
            logging_level = self.engine_config.logging_level or "WARNING"
            pool_logger = self.engine_config.logging_name or "sqlalchemy.pool"
            for logger in ("sqlalchemy", engine_logger, pool_logger):
                if logger not in logging_config.loggers:
                    logging_config.loggers[logger] = {
                        "level": logging_level,
                        "handlers": logging_config.loggers["starlite"]["handlers"],
                    }
