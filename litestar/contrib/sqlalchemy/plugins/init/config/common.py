from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, cast

from litestar.constants import HTTP_DISCONNECT, HTTP_RESPONSE_START, WEBSOCKET_CLOSE, WEBSOCKET_DISCONNECT
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.utils import get_litestar_scope_state, set_litestar_scope_state
from litestar.utils.dataclass import simple_asdict

from .engine import EngineConfig

if TYPE_CHECKING:
    from typing import Any

    from sqlalchemy import Connection, Engine
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import Mapper, Query, Session, sessionmaker
    from sqlalchemy.orm.session import JoinTransactionMode
    from sqlalchemy.sql import TableClause

    from litestar import Litestar
    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, EmptyType, Scope

__all__ = (
    "SESSION_SCOPE_KEY",
    "SESSION_TERMINUS_ASGI_EVENTS",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
)

SESSION_SCOPE_KEY = "_sqlalchemy_db_session"
SESSION_TERMINUS_ASGI_EVENTS = {HTTP_RESPONSE_START, HTTP_DISCONNECT, WEBSOCKET_DISCONNECT, WEBSOCKET_CLOSE}

ConnectionT = TypeVar("ConnectionT", bound="Connection | AsyncConnection")
EngineT = TypeVar("EngineT", bound="Engine | AsyncEngine")
SessionT = TypeVar("SessionT", bound="Session | AsyncSession")
SessionMakerT = TypeVar("SessionMakerT", bound="sessionmaker | async_sessionmaker")


@dataclass
class GenericSessionConfig(Generic[ConnectionT, EngineT, SessionT]):
    """SQLAlchemy async session config."""

    autobegin: bool | EmptyType = Empty
    """Automatically start transactions when database access is requested by an operation."""
    autoflush: bool | EmptyType = Empty
    """When ``True``, all query operations will issue a flush call to this :class:`Session <sqlalchemy.orm.Session>`
    before proceeding"""
    bind: EngineT | ConnectionT | None | EmptyType = Empty
    """The :class:`Engine <sqlalchemy.engine.Engine>` or :class:`Connection <sqlalchemy.engine.Connection>` that new
    :class:`Session <sqlalchemy.orm.Session>` objects will be bound to."""
    binds: dict[type[Any] | Mapper | TableClause | str, EngineT | ConnectionT] | None | EmptyType = Empty
    """A dictionary which may specify any number of :class:`Engine <sqlalchemy.engine.Engine>` or :class:`Connection
    <sqlalchemy.engine.Connection>` objects as the source of connectivity for SQL operations on a per-entity basis. The
    keys of the dictionary consist of any series of mapped classes, arbitrary Python classes that are bases for mapped
    classes, :class:`Table <sqlalchemy.schema.Table>` objects and :class:`Mapper <sqlalchemy.orm.Mapper>` objects. The
    values of the dictionary are then instances of :class:`Engine <sqlalchemy.engine.Engine>` or less commonly
    :class:`Connection <sqlalchemy.engine.Connection>` objects."""
    class_: type[SessionT] | EmptyType = Empty
    """Class to use in order to create new :class:`Session <sqlalchemy.orm.Session>` objects."""
    expire_on_commit: bool | EmptyType = Empty
    """If ``True``, all instances will be expired after each commit."""
    info: dict[str, Any] | None | EmptyType = Empty
    """Optional dictionary of information that will be available via the
    :attr:`Session.info <sqlalchemy.orm.Session.info>`"""
    join_transaction_mode: JoinTransactionMode | EmptyType = Empty
    """Describes the transactional behavior to take when a given bind is a Connection that has already begun a
    transaction outside the scope of this Session; in other words the
    :attr:`Connection.in_transaction() <sqlalchemy.Connection.in_transaction>` method returns True."""
    query_cls: type[Query] | None | EmptyType = Empty
    """Class which should be used to create new Query objects, as returned by the
    :attr:`Session.query() <sqlalchemy.orm.Session.query>` method."""
    twophase: bool | EmptyType = Empty
    """When ``True``, all transactions will be started as a “two phase” transaction, i.e. using the “two phase”
    semantics of the database in use along with an XID. During a :attr:`commit() <sqlalchemy.orm.Session.commit>`, after
    :attr:`flush() <sqlalchemy.orm.Session.flush>` has been issued for all attached databases, the
    :attr:`TwoPhaseTransaction.prepare() <sqlalchemy.engine.TwoPhaseTransaction.prepare>` method on each database`s
    :class:`TwoPhaseTransaction <sqlalchemy.engine.TwoPhaseTransaction>` will be called. This allows each database to
    roll back the entire transaction, before each transaction is committed."""


@dataclass
class GenericSQLAlchemyConfig(Generic[EngineT, SessionT, SessionMakerT]):
    """Common SQLAlchemy Configuration."""

    create_engine_callable: Callable[[str], EngineT]
    """Callable that creates an :class:`AsyncEngine <sqlalchemy.ext.asyncio.AsyncEngine>` instance or instance of its
    subclass.
    """
    session_config: GenericSessionConfig[Any, Any, Any]
    """Configuration options for either the :class:`async_sessionmaker <sqlalchemy.ext.asyncio.async_sessionmaker>`
    or :class:`sessionmaker <sqlalchemy.orm.sessionmaker>`.
    """
    session_maker_class: type[sessionmaker] | type[async_sessionmaker]
    """Sessionmaker class to use."""
    before_send_handler: BeforeMessageSendHookHandler
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if its still open, and committing and
    uncommitted data.
    """
    connection_string: str | None = field(default=None)
    """Database connection string in one of the formats supported by SQLAlchemy.

    Notes:
        - For async connections, the connection string must include the correct async prefix.
          e.g. ``'postgresql+asyncpg://...'`` instead of ``'postgresql://'``, and for sync connections its the opposite.

    """
    engine_dependency_key: str = "db_engine"
    """Key to use for the dependency injection of database engines."""
    session_dependency_key: str = "db_session"
    """Key to use for the dependency injection of database sessions."""
    engine_app_state_key: str = "db_engine"
    """Key under which to store the SQLAlchemy engine in the application :class:`State <.datastructures.State>`
    instance.
    """
    engine_config: EngineConfig = field(default_factory=EngineConfig)
    """Configuration for the SQLAlchemy engine.

    The configuration options are documented in the SQLAlchemy documentation.
    """
    session_maker_app_state_key: str = "session_maker_class"
    """Key under which to store the SQLAlchemy :class:`sessionmaker <sqlalchemy.orm.sessionmaker>` in the application
    :class:`State <.datastructures.State>` instance.
    """
    session_maker: Callable[[], SessionT] | None = None
    """Callable that returns a session.

    If provided, the plugin will use this rather than instantiate a sessionmaker.
    """
    engine_instance: EngineT | None = None
    """Optional engine to use.

    If set, the plugin will use the provided instance rather than instantiate an engine.
    """

    def __post_init__(self) -> None:
        if self.connection_string is not None and self.engine_instance is not None:
            raise ImproperlyConfiguredException("Only one of 'connection_string' or 'engine_instance' can be provided.")

    @property
    def engine_config_dict(self) -> dict[str, Any]:
        """Return the engine configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy :func:`create_engine <sqlalchemy.create_engine>`
            function.
        """
        return simple_asdict(self.engine_config, exclude_empty=True)

    @property
    def session_config_dict(self) -> dict[str, Any]:
        """Return the session configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the SQLAlchemy :class:`sessionmaker <sqlalchemy.orm.sessionmaker>`
            class.
        """
        return simple_asdict(self.session_config, exclude_empty=True)

    @property
    def signature_namespace(self) -> dict[str, Any]:
        """Return the plugin's signature namespace.

        Returns:
            A string keyed dict of names to be added to the namespace for signature forward reference resolution.
        """
        return {}  # pragma: no cover

    def create_engine(self) -> EngineT:
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
            self.engine_instance = self.create_engine_callable(self.connection_string, **engine_config)
        except TypeError:
            # likely due to a dialect that doesn't support json type
            del engine_config["json_deserializer"]
            del engine_config["json_serializer"]
            self.engine_instance = self.create_engine_callable(self.connection_string, **engine_config)

        return self.engine_instance

    def create_session_maker(self) -> Callable[[], SessionT]:
        """Get a session maker. If none exists yet, create one.

        Returns:
            Session factory used by the plugin.
        """
        if self.session_maker:
            return self.session_maker

        session_kws = self.session_config_dict
        if session_kws.get("bind") is None:
            session_kws["bind"] = self.create_engine()
        return self.session_maker_class(**session_kws)

    def provide_engine(self, state: State) -> EngineT:
        """Create an engine instance.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            An engine instance.
        """
        return cast("EngineT", state.get(self.engine_app_state_key))

    def provide_session(self, state: State, scope: Scope) -> SessionT:
        """Create a session instance.

        Args:
            state: The ``Litestar.state`` instance.
            scope: The current connection's scope.

        Returns:
            A session instance.
        """
        session = cast("SessionT | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
        if session is None:
            session_maker = cast("Callable[[], SessionT]", state[self.session_maker_app_state_key])
            session = session_maker()
            set_litestar_scope_state(scope, SESSION_SCOPE_KEY, session)
        return session

    def create_app_state_items(self) -> dict[str, Any]:
        """Key/value pairs to be stored in application state."""
        return {
            self.engine_app_state_key: self.create_engine(),
            self.session_maker_app_state_key: self.create_session_maker(),
        }

    def update_app_state(self, app: Litestar) -> None:
        """Set the app state with engine and session.

        Args:
            app: The ``Litestar`` instance.
        """
        app.state.update(self.create_app_state_items())
