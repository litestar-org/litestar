import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar, cast

import pydantic
import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeMeta,
    Mapped,
    declarative_mixin,
    registry,
    sessionmaker,
)

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import BooleanClauseList


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


def create_session_model(base: type[DeclarativeMeta]) -> type[DeclarativeMeta]:
    class SessionModel(base, SessionModelMixin):  # type: ignore[valid-type, misc]
        id: Mapped[int] = sa.Column(sa.Integer, primary_key=True)  # pyright: ignore

    return SessionModel


T = TypeVar("T", bound=SessionModelMixin)


def register_session_model(model: type[T], registry_: registry) -> type[T]:
    return registry_.mapped(model)


class SQLAlchemySessionConfig(ServerSideSessionConfig):
    model: Type[SessionModelMixin]
    plugin: Optional[SQLAlchemyPlugin]
    session_maker: Optional[sessionmaker]

    @pydantic.root_validator(pre=True)
    def validate(  # pylint: disable=no-self-argument
        cls: Type["SQLAlchemySessionConfig"], values: Dict[str, Any]
    ) -> Dict[str, Any]:
        plugin = values.get("plugin")
        session_maker = values.get("session_maker")
        if not session_maker or plugin and plugin._config:  # pylint: disable=protected-access
            raise ValueError(
                "Need to pass either a sessionmaker or a configured plugin to establish a database connection"
            )

        return values


class SQLAlchemyBackend(ServerSideBackend[SQLAlchemySessionConfig]):
    # TODO: Handle sync sessions

    def __init__(self, config: SQLAlchemySessionConfig) -> None:
        super().__init__(config=config)
        self._model = config.model
        self._session_maker = cast("sessionmaker", config.session_maker or config.plugin._config.session_maker)

    def _create_sa_session(self) -> "AsyncSession":
        return cast("AsyncSession", self._session_maker)

    async def _get_session_obj(self, *, sa_session: "AsyncSession", session_id: str) -> Optional[SessionModelMixin]:
        result = await sa_session.scalars(sa.select(self._model).where(self._model.session_id == session_id))
        return result.one_or_none()

    def _update_session_expiry(self, session_obj: SessionModelMixin) -> None:
        session_obj.expires = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(
            seconds=self.config.max_age
        )

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
