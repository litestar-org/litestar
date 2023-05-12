"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

from asyncio import AbstractEventLoop, get_event_loop_policy
from pathlib import Path
from typing import Any, AsyncGenerator, Iterator

import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.contrib.sqlalchemy.models import AuthorRepository, BookRepository
from tests.contrib.sqlalchemy.repository import sqlalchemy_tests as st


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(name="engine")
async def fx_engine(tmp_path: Path) -> AsyncGenerator[AsyncEngine, None]:
    """SQLite engine for end-to-end testing.

    Returns:
        Async SQLAlchemy engine instance.
    """
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path}/test.db",
        echo=True,
        poolclass=NullPool,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(
    name="session",
)
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


@pytest.fixture(name="author_repo")
def fx_author_repo(session: AsyncSession) -> AuthorRepository:
    return AuthorRepository(session=session)


@pytest.fixture(name="book_repo")
def fx_book_repo(session: AsyncSession) -> BookRepository:
    return BookRepository(session=session)


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_filter_by_kwargs_with_incorrect_attribute_name(author_repo=author_repo)


async def test_repo_count_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy count with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_count_method(author_repo=author_repo)


async def test_repo_list_and_count_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with count in aiosqlite.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_and_count_method(raw_authors=raw_authors, author_repo=author_repo)


async def test_repo_list_and_count_method_empty(book_repo: BookRepository) -> None:
    """Test SQLALchemy list with count in aiosqlite.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    await st.test_repo_list_and_count_method_empty(book_repo=book_repo)


async def test_repo_list_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with aiosqlite.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_list_method(raw_authors=raw_authors, author_repo=author_repo)


async def test_repo_add_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add with aiosqlite.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_method(raw_authors=raw_authors, author_repo=author_repo)


async def test_repo_add_many_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add Many with aiosqlite.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_add_many_method(raw_authors=raw_authors, author_repo=author_repo)


async def test_repo_update_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update Many with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_many_method(author_repo=author_repo)


async def test_repo_exists_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy exists with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_exists_method(author_repo=author_repo)


async def test_repo_update_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_update_method(author_repo=author_repo)


async def test_repo_delete_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_method(author_repo=author_repo)


async def test_repo_delete_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete many with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_delete_many_method(author_repo=author_repo)


async def test_repo_get_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_method(author_repo=author_repo)


async def test_repo_get_one_or_none_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_or_none_method(author_repo=author_repo)


async def test_repo_get_one_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_one_method(author_repo=author_repo)


async def test_repo_get_or_create_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_method(author_repo=author_repo)


async def test_repo_get_or_create_match_filter(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_get_or_create_match_filter(author_repo=author_repo)


async def test_repo_upsert_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy upsert with aiosqlite.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    await st.test_repo_upsert_method(author_repo=author_repo)
