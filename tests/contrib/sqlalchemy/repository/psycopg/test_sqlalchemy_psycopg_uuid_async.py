"""Unit tests for the SQLAlchemy Repository implementation for psycopg."""
from __future__ import annotations

import sys
from typing import Any, AsyncGenerator

import pytest
from sqlalchemy import NullPool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.contrib.sqlalchemy.models_uuid import (
    AuthorAsyncRepository,
    BookAsyncRepository,
)
from tests.contrib.sqlalchemy.repository import sqlalchemy_async_uuid_tests as st

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="docker not available on this platform"),
    pytest.mark.usefixtures("postgres_service"),
    pytest.mark.sqlalchemy_integration,
]


@pytest.mark.sqlalchemy_psycopg_async
@pytest.fixture(name="engine")
async def fx_engine(docker_ip: str) -> AsyncEngine:
    """Postgresql instance for end-to-end testing.

    Args:
        docker_ip: IP address for TCP connection to Docker containers.

    Returns:
        Async SQLAlchemy engine instance.
    """
    return create_async_engine(
        URL(
            drivername="postgresql+psycopg",
            username="postgres",
            password="super-secret",
            host=docker_ip,
            port=5423,
            database="postgres",
            query={},  # type:ignore[arg-type]
        ),
        echo=True,
        poolclass=NullPool,
    )


@pytest.mark.sqlalchemy_psycopg_async
@pytest.fixture(
    name="session",
)
async def fx_session(
    engine: AsyncEngine, raw_authors_uuid: list[dict[str, Any]], raw_books_bigint: list[dict[str, Any]]
) -> AsyncGenerator[AsyncSession, None]:
    session = async_sessionmaker(bind=engine)()
    await st.seed_db(engine, raw_authors_uuid, raw_books_bigint)
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest.mark.sqlalchemy_psycopg_async
@pytest.fixture(name="author_repo")
def fx_author_repo(session: AsyncSession) -> AuthorAsyncRepository:
    return AuthorAsyncRepository(session=session)


@pytest.mark.sqlalchemy_psycopg_async
@pytest.fixture(name="book_repo")
def fx_book_repo(session: AsyncSession) -> BookAsyncRepository:
    return BookAsyncRepository(session=session)


@pytest.mark.sqlalchemy_psycopg_async
def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_filter_by_kwargs_with_incorrect_attribute_name(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_count_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_count_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_list_and_count_method(
    raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository
) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_and_count_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_list_and_count_method_empty(book_repo: BookAsyncRepository) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    await st.test_repo_list_and_count_method_empty(book_repo=book_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_list_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_add_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_add_many_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_many_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_update_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_many_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_exists_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_exists_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_update_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_delete_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_delete_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_many_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_get_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_get_one_or_none_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_or_none_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_get_one_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_get_or_create_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_get_or_create_match_filter(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_match_filter(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_upsert_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_upsert_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_filter_before_after(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy BeforeAfter filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_filter_before_after(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_filter_search(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Search filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_filter_search(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_filter_order_by(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Order By filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_filter_order_by(author_repo=author_repo)


@pytest.mark.sqlalchemy_psycopg_async
async def test_repo_filter_collection(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Collection filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_filter_collection(author_repo=author_repo)
