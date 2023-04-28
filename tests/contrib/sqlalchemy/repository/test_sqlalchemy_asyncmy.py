"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import NullPool, insert
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.sqlalchemy import base
from tests.contrib.sqlalchemy.models import Author, AuthorRepository, BookRepository

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="docker not available on this platform"),
    pytest.mark.usefixtures("mysql_service"),
]


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
@pytest.fixture(name="raw_authors")
def fx_raw_authors() -> list[dict[str, Any]]:
    """Unstructured author representations."""
    return [
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
        {
            "id": "5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2",
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="raw_books")
def fx_raw_books(raw_authors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unstructured book representations."""
    return [
        {
            "id": UUID("f34545b9-663c-4fce-915d-dd1ae9cea42a"),
            "title": "Murder on the Orient Express",
            "author_id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
            "author": raw_authors[0],
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="raw_log_events")
def fx_raw_log_events() -> list[dict[str, Any]]:
    """Unstructured log events representations."""
    return [
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea42a",
            "logged_at": "0001-01-01T00:00:00",
            "payload": {"foo": "bar", "baz": datetime.now()},
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


async def _seed_db(engine: AsyncEngine, raw_authors: list[dict[str, Any]], raw_books: list[dict[str, Any]]) -> None:
    """Populate test database with sample data.

    Args:
        engine: The SQLAlchemy engine instance.
    """
    # convert date/time strings to dt objects.
    for raw_author in raw_authors:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d")
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S")
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S")

    async with engine.begin() as conn:
        await conn.run_sync(base.orm_registry.metadata.drop_all)
        await conn.run_sync(base.orm_registry.metadata.create_all)
        await conn.execute(insert(Author).values(raw_authors))


@pytest.mark.sqlalchemy_asyncmy
@pytest.fixture(name="session")
async def fx_session(
    engine: AsyncEngine, raw_authors: list[dict[str, Any]], raw_books: list[dict[str, Any]]
) -> AsyncGenerator[AsyncSession, None]:
    session = async_sessionmaker(bind=engine)()
    await _seed_db(engine, raw_authors, raw_books)
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
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_count_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy count with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    assert await author_repo.count() == 2


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_and_count_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with count in asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    exp_count = len(raw_authors)
    collection, count = await author_repo.list_and_count()
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_and_count_method_empty(book_repo: BookRepository) -> None:
    """Test SQLALchemy list with count in asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    collection, count = await book_repo.list_and_count()
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_list_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    exp_count = len(raw_authors)
    collection = await author_repo.list()
    assert isinstance(collection, list)
    assert len(collection) == exp_count


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_add_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    exp_count = len(raw_authors) + 1
    new_author = Author(name="Testing", dob=datetime.now())
    obj = await author_repo.add(new_author)
    count = await author_repo.count()
    assert exp_count == count
    assert isinstance(obj, Author)
    assert new_author.name == obj.name
    assert obj.id is not None


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_add_many_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Add Many with asyncmy.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    exp_count = len(raw_authors) + 2
    objs = await author_repo.add_many(
        [Author(name="Testing 2", dob=datetime.now()), Author(name="Cody", dob=datetime.now())]
    )
    count = await author_repo.count()
    assert exp_count == count
    assert isinstance(objs, list)
    assert len(objs) == 2
    for obj in objs:
        assert obj.id is not None
        assert obj.name in {"Testing 2", "Cody"}


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_update_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update Many with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    objs = await author_repo.list()
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = await author_repo.update_many(objs)
    for obj in objs:
        assert obj.name.startswith("Update")


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_exists_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy exists with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    exists = await author_repo.exists(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert exists


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_update_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Update with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = await author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    obj.name = "Updated Name"
    updated_obj = await author_repo.update(obj)
    assert updated_obj.name == obj.name


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_delete_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = await author_repo.delete(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_delete_many_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy delete many with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    data_to_insert = []
    for chunk in range(0, 1000):
        data_to_insert.append(
            Author(
                name="author name %d" % chunk,
            )
        )
    _ = await author_repo.add_many(data_to_insert)
    all_objs = await author_repo.list()
    ids_to_delete = [existing_obj.id for existing_obj in all_objs]
    objs = await author_repo.delete_many(ids_to_delete)
    await author_repo.session.commit()
    assert len(objs) > 0
    data, count = await author_repo.list_and_count()
    assert data == []
    assert count == 0


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = await author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.name == "Agatha Christie"


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_one_or_none_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = await author_repo.get_one_or_none(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await author_repo.get_one_or_none(name="I don't exist")
    assert none_obj is None


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_one_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get One with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = await author_repo.get_one(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await author_repo.get_one(name="I don't exist")


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_or_create_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    existing_obj, existing_created = await author_repo.get_or_create(name="Agatha Christie")
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_created is False
    new_obj, new_created = await author_repo.get_or_create(name="New Author")
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_get_or_create_match_filter(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    now = datetime.now()
    existing_obj, existing_created = await author_repo.get_or_create(
        match_fields="name", name="Agatha Christie", dob=now
    )
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_obj.dob == now
    assert existing_created is False


@pytest.mark.sqlalchemy_asyncmy
async def test_repo_upsert_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy upsert with asyncmy.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    existing_obj = await author_repo.get_one(name="Agatha Christie")
    existing_obj.name = "Agatha C."
    upsert_update_obj = await author_repo.upsert(existing_obj)
    assert upsert_update_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = await author_repo.upsert(Author(name="An Author"))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = await author_repo.upsert(Author(id=uuid4(), name="Another Author"))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"
