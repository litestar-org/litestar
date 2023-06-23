from asyncio import sleep
from datetime import datetime
from typing import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import FetchedValue

from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository

pytestmark = [pytest.mark.sqlalchemy_integration]


class Base(DeclarativeBase):
    ...


class WithUpdatedField(Base):
    __tablename__ = "with_updated_field"

    id: Mapped[int] = mapped_column(primary_key=True)
    val: Mapped[int]
    updated: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue()
    )


@pytest.fixture(name="mysql_engine")
async def fixture_mysql_engine(asyncmy_engine: AsyncEngine) -> AsyncGenerator[AsyncEngine, None]:
    async with asyncmy_engine.begin() as conn:
        await conn.run_sync(WithUpdatedField.__table__.create)  # type:ignore[attr-defined]
    yield asyncmy_engine
    async with asyncmy_engine.begin() as conn:
        await conn.run_sync(WithUpdatedField.__table__.drop)  # type:ignore[attr-defined]


@pytest.fixture(name="session")
async def fixture_session(mysql_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session = async_sessionmaker(bind=mysql_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest.fixture(name="repo")
async def fixture_repo(session: AsyncSession) -> SQLAlchemyAsyncRepository:
    class Repo(SQLAlchemyAsyncRepository[WithUpdatedField]):  # type:ignore[type-var]
        model_type = WithUpdatedField

    return Repo(session=session)


async def test_async_add(repo: SQLAlchemyAsyncRepository) -> None:
    added = await repo.add(WithUpdatedField(val=1))
    assert "updated" in vars(added)


async def test_async_update(repo: SQLAlchemyAsyncRepository) -> None:
    added = await repo.add(WithUpdatedField(val=1))
    first_update = added.updated
    await sleep(1)
    added.val = 2
    updated = await repo.update(added)
    assert updated.updated > first_update


async def test_async_upsert(repo: SQLAlchemyAsyncRepository) -> None:
    added = await repo.add(WithUpdatedField(val=1))
    assert "updated" in vars(added)


async def test_async_get_or_create(repo: SQLAlchemyAsyncRepository) -> None:
    added, _ = await repo.get_or_create(val=1)
    assert "updated" in vars(added)
