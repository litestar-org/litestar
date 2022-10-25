import abc
import datetime
from typing import Generic, Optional, TYPE_CHECKING, Type, TypeVar, Union, cast

import anyio.to_thread
import sqlalchemy as sa
from pydantic import validator
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSASession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeMeta, Mapped
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import declarative_mixin, registry

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

if TYPE_CHECKING:
    from sqlalchemy.sql import Select
    from sqlalchemy.sql.elements import BooleanClauseList


AnySASession = Union[SASession, AsyncSASession]
AnySAessionT = TypeVar("AnySAessionT", bound=AnySASession)


@declarative_mixin
class SessionModelMixin:
    session_id: Mapped[str] = sa.Column(sa.String, nullable=False, unique=True, index=True)  # pyright: ignore
    data: Mapped[bytes] = sa.Column(sa.BLOB, nullable=False)  # pyright: ignore
    expires: Mapped[datetime.datetime] = sa.Column(sa.DateTime, nullable=False)  # pyright: ignore

    @hybrid_property
    def expired(self) -> bool:  # pyright: ignore
        return datetime.datetime.utcnow().replace(tzinfo=None) > self.expires

    @expired.expression  # type: ignore[no-redef]
    def expired(cls) -> "BooleanClauseList":  # pylint: disable=no-self-argument
        return datetime.datetime.utcnow().replace(tzinfo=None) > cls.expires  # pyright: ignore


def create_session_model(base: type[DeclarativeMeta], table_name: str = "session") -> type[SessionModelMixin]:
    class SessionModel(base, SessionModelMixin):  # type: ignore[valid-type, misc]
        __tablename__ = table_name
        id: Mapped[int] = sa.Column(sa.Integer, primary_key=True)  # pyright: ignore

    return SessionModel


SessionModelT = TypeVar("SessionModelT", bound=SessionModelMixin)


def register_session_model(model: type[SessionModelT], registry_: registry) -> type[SessionModelT]:
    return registry_.mapped(model)


class BaseSQLAlchemySessionBackend(Generic[AnySAessionT], ServerSideBackend["SQLAlchemyBackendConfig"], abc.ABC):
    def __init__(self, config: "SQLAlchemyBackendConfig") -> None:
        super().__init__(config=config)
        self._model = config.model
        self._session_maker = cast("SQLAlchemyPluginConfig", config.plugin._config).session_maker

    def _create_sa_session(self) -> AnySAessionT:
        return cast("S", self._session_maker())

    def _select_session_obj(self, session_id: str) -> "Select":
        return sa.select(self._model).where(self._model.session_id == session_id)

    def _update_session_expiry(self, session_obj: SessionModelMixin) -> None:
        session_obj.expires = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(
            seconds=self.config.max_age
        )

    @abc.abstractmethod
    async def delete_expired(self) -> None:
        """Delete all expired session from the database."""


class AsyncSQLAlchemyBackend(BaseSQLAlchemySessionBackend[AsyncSASession]):
    async def _get_session_obj(self, *, sa_session: AsyncSASession, session_id: str) -> Optional[SessionModelMixin]:
        result = await sa_session.scalars(self._select_session_obj(session_id))
        return result.one_or_none()

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associate with `session_id`.

        If no data for the given `session_id` exists, return an empty
        dict
        """
        sa_session = self._create_sa_session()
        session_obj = await self._get_session_obj(sa_session=sa_session, session_id=session_id)
        if session_obj:
            if not session_obj.expired:
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
        """
        sa_session = self._create_sa_session()
        session_obj = await self._get_session_obj(sa_session=sa_session, session_id=session_id)

        if not session_obj:
            session_obj = self._model(session_id=session_id)  # type: ignore[call-arg]
            sa_session.add(session_obj)
        session_obj.data = data
        self._update_session_expiry(session_obj)
        await sa_session.commit()

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`"""
        sa_session = self._create_sa_session()
        await sa_session.execute(sa.delete(self._model).where(self._model.session_id == session_id))
        await sa_session.commit()

    async def delete_all(self) -> None:
        """Delete all data stored within this backend."""
        sa_session = self._create_sa_session()

        await sa_session.execute(sa.delete(self._model))
        await sa_session.commit()

    async def delete_expired(self) -> None:
        """Delete all expired session from the database."""
        sa_session = self._create_sa_session()
        await sa_session.execute(sa.delete(self._model).where(self._model.expired))


class SQLAlchemyBackend(BaseSQLAlchemySessionBackend[SASession]):
    def _get_session_obj(self, *, sa_session: SASession, session_id: str) -> Optional[SessionModelMixin]:
        return sa_session.scalars(self._select_session_obj(session_id)).one_or_none()

    def _get(self, session_id: str) -> Optional[bytes]:
        sa_session = self._create_sa_session()
        session_obj = self._get_session_obj(sa_session=sa_session, session_id=session_id)

        if session_obj:
            if not session_obj.expired:
                self._update_session_expiry(session_obj)  # type: ignore[unreachable]
                sa_session.commit()
                return session_obj.data
            sa_session.delete(session_obj)
            sa_session.commit()
        return None

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associate with `session_id`.

        If no data for the given `session_id` exists, return an empty
        dict
        """
        return await anyio.to_thread.run_sync(self._get, session_id)

    def _set(self, session_id: str, data: bytes) -> None:
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
        """
        return await anyio.to_thread.run_sync(self._set, session_id, data)

    def _delete(self, session_id: str) -> None:
        sa_session = self._create_sa_session()
        sa_session.execute(sa.delete(self._model).where(self._model.session_id == session_id))
        sa_session.commit()

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`"""
        return await anyio.to_thread.run_sync(self._delete, session_id)

    def _delete_all(self) -> None:
        sa_session = self._create_sa_session()

        sa_session.execute(sa.delete(self._model))
        sa_session.commit()

    async def delete_all(self) -> None:
        """Delete all data stored within this backend."""
        await anyio.to_thread.run_sync(self._delete_all)

    def _delete_expired(self) -> None:
        sa_session = self._create_sa_session()
        sa_session.execute(sa.delete(self._model).where(self._model.expired))

    async def delete_expired(self) -> None:
        """Delete all expired session from the database."""
        await anyio.to_thread.run_sync(self._delete_expired)


class SQLAlchemyBackendConfig(ServerSideSessionConfig):
    model: Type[SessionModelMixin]
    plugin: SQLAlchemyPlugin

    @validator("plugin", always=True)
    def validate_plugin_config(cls, value: SQLAlchemyPlugin) -> SQLAlchemyPlugin:
        if not (value._config and value._config.session_maker):
            raise ValueError("Plugin needs to be configured")
        return value

    @property
    def _backend_class(self) -> Type[BaseSQLAlchemySessionBackend]:  # type: ignore[override]
        if cast("SQLAlchemyPluginConfig", self.plugin._config).use_async_engine:
            return AsyncSQLAlchemyBackend
        return SQLAlchemyBackend
