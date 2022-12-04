from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Generic, Optional, Type, TypeVar, Union, cast

import sqlalchemy as sa
from anyio.to_thread import run_sync
from pydantic import validator
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSASession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import declarative_mixin, registry

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

if TYPE_CHECKING:
    from sqlalchemy.sql import Select
    from sqlalchemy.sql.elements import BooleanClauseList

    from starlite.plugins.sql_alchemy import SQLAlchemyConfig as SQLAlchemyPluginConfig


AnySASession = Union[SASession, AsyncSASession]
AnySASessionT = TypeVar("AnySASessionT", bound=AnySASession)
SessionModelT = TypeVar("SessionModelT", bound="SessionModelMixin")


@declarative_mixin
class SessionModelMixin:
    """Mixin for session storage."""

    session_id: Mapped[str] = sa.Column(sa.String, nullable=False, unique=True, index=True)  # pyright: ignore
    data: Mapped[bytes] = sa.Column(sa.LargeBinary, nullable=False)  # pyright: ignore
    expires: Mapped[datetime] = sa.Column(sa.DateTime, nullable=False)  # pyright: ignore

    @hybrid_property
    def expired(self) -> bool:  # pyright: ignore
        """Boolean indicating if the session has expired."""
        return datetime.utcnow().replace(tzinfo=None) > self.expires

    @expired.expression  # type: ignore[no-redef]
    def expired(cls) -> "BooleanClauseList":  # pylint: disable=no-self-argument
        """SQL-Expression to check if the session has expired."""
        return datetime.utcnow().replace(tzinfo=None) > cls.expires  # pyright: ignore


class SessionModel(SessionModelMixin):
    """Session storage model."""

    __tablename__ = "session"
    id: Mapped[int] = sa.Column(sa.Integer, primary_key=True)  # pyright: ignore


def create_session_model(base: Type[Any], table_name: str = "session") -> Type[SessionModelMixin]:
    """Dynamically generate a session storage model and register it with the declarative base.

    Args:
        base: SQLAlchemy declarative base
        table_name: Alternative table name

    Returns:
        A mapped model subclassing `base` and `SessionModelMixin`
    """

    class Model(base, SessionModelMixin):  # type: ignore[valid-type,misc]
        __tablename__ = table_name
        id: Mapped[int] = sa.Column(sa.Integer, primary_key=True)  # pyright: ignore

    return Model


def register_session_model(base: Union[registry, Any], model: Type[SessionModelT]) -> Type[SessionModelT]:
    """Map and register a pre-existing model subclassing `SessionModelMixin` with a declarative base or registry.

    Args:
        base: Either a `orm.registry` or `DeclarativeBase`
        model: SQLAlchemy model to register

    Returns:
        A mapped model subclassing `SessionModelMixin`, and registered in `registry`
    """
    registry_ = base.registry if not isinstance(base, registry) else base
    return cast("Type[SessionModelT]", registry_.map_declaratively(model))


class BaseSQLAlchemyBackend(Generic[AnySASessionT], ServerSideBackend["SQLAlchemyBackendConfig"], ABC):
    """Session backend to store data in a database with SQLAlchemy. Works with both sync and async engines.

    Notes:
        - Requires `sqlalchemy` which needs to be installed separately, and a configured
        [SQLAlchemyPlugin][starlite.plugins.sql_alchemy.SQLAlchemyPlugin].
    """

    __slots__ = ("_model", "_session_maker")

    def __init__(self, config: "SQLAlchemyBackendConfig") -> None:
        """Initialize `BaseSQLAlchemyBackend`.

        Args:
            config: An instance of `SQLAlchemyBackendConfig`
        """
        super().__init__(config=config)
        self._model = config.model
        self._session_maker = cast("SQLAlchemyPluginConfig", config.plugin._config).session_maker

    def _create_sa_session(self) -> AnySASessionT:
        return cast("AnySASessionT", self._session_maker())

    def _select_session_obj(self, session_id: str) -> "Select":
        return sa.select(self._model).where(self._model.session_id == session_id)

    def _update_session_expiry(self, session_obj: SessionModelMixin) -> None:
        session_obj.expires = datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age)

    @abstractmethod
    async def delete_expired(self) -> None:
        """Delete all expired sessions from the database."""


class AsyncSQLAlchemyBackend(BaseSQLAlchemyBackend[AsyncSASession]):
    """Asynchronous SQLAlchemy backend."""

    async def _get_session_obj(self, *, sa_session: AsyncSASession, session_id: str) -> Optional[SessionModelMixin]:
        result = await sa_session.scalars(self._select_session_obj(session_id))
        return result.one_or_none()

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associated with `session_id`.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """
        async with self._create_sa_session() as sa_session:
            session_obj = await self._get_session_obj(sa_session=sa_session, session_id=session_id)
            if session_obj:
                if not session_obj.expired:  # type: ignore[truthy-function]
                    self._update_session_expiry(session_obj)  # type: ignore[unreachable]
                    await sa_session.commit()
                    return session_obj.data
                await sa_session.delete(session_obj)
                await sa_session.commit()
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` under the `session_id` for later retrieval.

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time

        Args:
            session_id: The session-ID.
            data: Serialized session data

        Returns:
            None
        """
        async with self._create_sa_session() as sa_session:
            session_obj = await self._get_session_obj(sa_session=sa_session, session_id=session_id)

            if not session_obj:
                session_obj = self._model(session_id=session_id)  # type: ignore[call-arg]
                sa_session.add(session_obj)
            session_obj.data = data
            self._update_session_expiry(session_obj)
            await sa_session.commit()

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`. Fails silently if no such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        async with self._create_sa_session() as sa_session:
            await sa_session.execute(sa.delete(self._model).where(self._model.session_id == session_id))
            await sa_session.commit()

    async def delete_all(self) -> None:
        """Delete all session data.

        Returns:
            None
        """
        async with self._create_sa_session() as sa_session:
            await sa_session.execute(sa.delete(self._model))
            await sa_session.commit()

    async def delete_expired(self) -> None:
        """Delete all expired session from the database.

        Returns:
            None
        """
        async with self._create_sa_session() as sa_session:
            await sa_session.execute(sa.delete(self._model).where(self._model.expired))
            await sa_session.commit()


class SQLAlchemyBackend(BaseSQLAlchemyBackend[SASession]):
    """Synchronous SQLAlchemy backend."""

    def _get_session_obj(self, *, sa_session: SASession, session_id: str) -> Optional[SessionModelMixin]:
        return sa_session.scalars(self._select_session_obj(session_id)).one_or_none()

    def _get_sync(self, session_id: str) -> Optional[bytes]:
        sa_session = self._create_sa_session()
        session_obj = self._get_session_obj(sa_session=sa_session, session_id=session_id)

        if session_obj:
            if not session_obj.expired:  # type: ignore[truthy-function]
                self._update_session_expiry(session_obj)  # type: ignore[unreachable]
                sa_session.commit()
                return session_obj.data
            sa_session.delete(session_obj)
            sa_session.commit()
        return None

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associated with `session_id`.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """
        return await run_sync(self._get_sync, session_id)

    def _set_sync(self, session_id: str, data: bytes) -> None:
        sa_session = self._create_sa_session()
        session_obj = self._get_session_obj(sa_session=sa_session, session_id=session_id)

        if not session_obj:
            session_obj = self._model(session_id=session_id)  # type: ignore[call-arg]
            sa_session.add(session_obj)
        session_obj.data = data
        self._update_session_expiry(session_obj)
        sa_session.commit()

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` under the `session_id` for later retrieval.

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        return await run_sync(self._set_sync, session_id, data)

    def _delete_sync(self, session_id: str) -> None:
        sa_session = self._create_sa_session()
        sa_session.execute(sa.delete(self._model).where(self._model.session_id == session_id))
        sa_session.commit()

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`. Fails silently if no such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        return await run_sync(self._delete_sync, session_id)

    def _delete_all_sync(self) -> None:
        sa_session = self._create_sa_session()

        sa_session.execute(sa.delete(self._model))
        sa_session.commit()

    async def delete_all(self) -> None:
        """Delete all session data.

        Returns:
            None
        """
        await run_sync(self._delete_all_sync)

    def _delete_expired_sync(self) -> None:
        sa_session = self._create_sa_session()
        sa_session.execute(sa.delete(self._model).where(self._model.expired))
        sa_session.commit()

    async def delete_expired(self) -> None:
        """Delete all expired session from the database.

        Returns:
            None
        """
        await run_sync(self._delete_expired_sync)


class SQLAlchemyBackendConfig(ServerSideSessionConfig):
    """Configuration for `SQLAlchemyBackend` and `AsyncSQLAlchemyBackend`"""

    model: Type[SessionModelMixin]
    plugin: SQLAlchemyPlugin

    @validator("plugin", always=True)
    def validate_plugin_config(cls, value: SQLAlchemyPlugin) -> SQLAlchemyPlugin:  # pylint: disable=no-self-argument)
        """Check if the SQLAlchemyPlugin is configured."""
        if not (value._config and value._config.session_maker):
            raise ValueError("Plugin needs to be configured")
        return value

    @property
    def _backend_class(self) -> Type[Union[SQLAlchemyBackend, AsyncSQLAlchemyBackend]]:  # type: ignore[override]
        """Return either `SQLAlchemyBackend` or `AsyncSQLAlchemyBackend`, depending on the engine type configured in the
        `SQLAlchemyPlugin`
        """
        if cast("SQLAlchemyPluginConfig", self.plugin._config).use_async_engine:
            return AsyncSQLAlchemyBackend
        return SQLAlchemyBackend
