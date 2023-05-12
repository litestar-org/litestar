"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

import sys
from asyncio import AbstractEventLoop, get_event_loop_policy
from typing import Any, AsyncGenerator, Iterator

import pytest
from sqlalchemy import NullPool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.contrib.sqlalchemy.models import AuthorRepository, BookRepository
from tests.contrib.sqlalchemy.repository import sqlalchemy_tests as st

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="docker not available on this platform"),
    pytest.mark.usefixtures("mysql_service"),
]


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.sqlalchemy_asyncmy
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
            drivername="mysql+asyncmy",
            username="app",
            password="super-secret",
            host=docker_ip,
            port=3360,
            database="db",
            query={},  # type:ignore[arg-type]
        ),
        echo=True,
        poolclass=NullPool,
    )


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="session")
async def fx_session(
    engine: AsyncEngine, raw_authors: list[dict[str, Any]], raw_books: list[dict[str, Any]]
) -> AsyncGenerator[AsyncSession, None]:
    session = async_sessionmaker(bind=engine)()
    await st.seed_db(engine, raw_authors, raw_books)
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="author_repo")
def fx_author_repo(session: AsyncSession) -> AuthorRepository:
    return AuthorRepository(session=session)


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="book_repo")
def fx_book_repo(session: AsyncSession) -> BookRepository:
    return BookRepository(session=session)


@pytest.mark.sqlalchemy_asyncmy
def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_filter_by_kwargs_with_incorrect_attribute_name(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_count_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy count with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_count_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_and_count_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with count in asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_and_count_method(raw_authors=raw_authors, author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_and_count_method_empty(book_repo: BookRepository) -> None:
    """Test SQLALchemy list with count in asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    await st.test_repo_list_and_count_method_empty(book_repo=book_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_method(raw_authors=raw_authors, author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_add_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_method(raw_authors=raw_authors, author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_add_many_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add Many with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_many_method(raw_authors=raw_authors, author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_update_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update Many with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_many_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_exists_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy exists with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_exists_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_update_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_delete_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_delete_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete many with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_many_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_one_or_none_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_or_none_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_one_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_or_create_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_method(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_or_create_match_filter(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_match_filter(author_repo=author_repo)


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_upsert_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy upsert with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_upsert_method(author_repo=author_repo)
