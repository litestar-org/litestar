"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
)

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, OrderBy, SearchFilter
from litestar.contrib.sqlalchemy import base
from tests.contrib.sqlalchemy.models_uuid import AuthorAsyncRepository, BookAsyncRepository, UUIDAuthor, UUIDRule


async def seed_db(
    engine: AsyncEngine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_books_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> None:
    """Populate test database with sample data.

    Args:
        engine: The SQLAlchemy engine instance.
    """
    # convert date/time strings to dt objects.
    for raw_author in raw_authors_uuid:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S")
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S")
    for raw_author in raw_rules_uuid:
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S")
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S")

    async with engine.begin() as conn:
        await conn.run_sync(base.orm_registry.metadata.drop_all)
        await conn.run_sync(base.orm_registry.metadata.create_all)
        await conn.execute(insert(UUIDAuthor).values(raw_authors_uuid))
        await conn.execute(insert(UUIDRule).values(raw_rules_uuid))


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


async def test_repo_count_method(
    author_repo: AuthorAsyncRepository,
) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    assert await author_repo.count() == 2


async def test_repo_list_and_count_method(
    raw_authors_uuid: list[dict[str, Any]],
    author_repo: AuthorAsyncRepository,
) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection, count = await author_repo.list_and_count()
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_list_and_count_method_empty(book_repo: BookAsyncRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    collection, count = await book_repo.list_and_count()
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


async def test_repo_list_method(
    raw_authors_uuid: list[dict[str, Any]],
    author_repo: AuthorAsyncRepository,
) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection = await author_repo.list()
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_add_method(
    raw_authors_uuid: list[dict[str, Any]],
    author_repo: AuthorAsyncRepository,
) -> None:
    """Test SQLALchemy Add.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid) + 1
    new_author = UUIDAuthor(name="Testing", dob=datetime.now())
    obj = await author_repo.add(new_author)
    count = await author_repo.count()
    assert exp_count == count
    assert isinstance(obj, UUIDAuthor)
    assert new_author.name == obj.name
    assert obj.id is not None


async def test_repo_add_many_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid) + 2
    objs = await author_repo.add_many(
        [UUIDAuthor(name="Testing 2", dob=datetime.now()), UUIDAuthor(name="Cody", dob=datetime.now())]
    )
    count = await author_repo.count()
    assert exp_count == count
    assert isinstance(objs, list)
    assert len(objs) == 2
    for obj in objs:
        assert obj.id is not None
        assert obj.name in {"Testing 2", "Cody"}


async def test_repo_update_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    objs = await author_repo.list()
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = await author_repo.update_many(objs)
    for obj in objs:
        assert obj.name.startswith("Update")


async def test_repo_exists_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exists = await author_repo.exists(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert exists


async def test_repo_update_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    obj.name = "Updated Name"
    updated_obj = await author_repo.update(obj)
    assert updated_obj.name == obj.name


async def test_repo_delete_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await author_repo.delete(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")


async def test_repo_delete_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    data_to_insert = []
    for chunk in range(0, 1000):
        data_to_insert.append(
            UUIDAuthor(
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


async def test_repo_get_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.name == "Agatha Christie"


async def test_repo_get_one_or_none_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await author_repo.get_one_or_none(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await author_repo.get_one_or_none(name="I don't exist")
    assert none_obj is None


async def test_repo_get_one_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await author_repo.get_one(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await author_repo.get_one(name="I don't exist")


async def test_repo_get_or_create_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj, existing_created = await author_repo.get_or_create(name="Agatha Christie")
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_created is False
    new_obj, new_created = await author_repo.get_or_create(name="New Author")
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


async def test_repo_get_or_create_match_filter(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    now = datetime.now()
    existing_obj, existing_created = await author_repo.get_or_create(
        match_fields="name", name="Agatha Christie", dob=now.date()
    )
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_obj.dob == now.date()
    assert existing_created is False


async def test_repo_upsert_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj = await author_repo.get_one(name="Agatha Christie")
    existing_obj.name = "Agatha C."
    upsert_update_obj = await author_repo.upsert(existing_obj)
    assert upsert_update_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = await author_repo.upsert(UUIDAuthor(name="An Author"))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = await author_repo.upsert(UUIDAuthor(id=uuid4(), name="Another Author"))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"


async def test_repo_filter_before_after(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy before after filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    before_filter = BeforeAfter(
        field_name="created", before=datetime.strptime("2023-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S"), after=None
    )
    existing_obj = await author_repo.list(before_filter)
    assert existing_obj[0].name == "Leo Tolstoy"

    after_filter = BeforeAfter(
        field_name="created", after=datetime.strptime("2023-03-01T00:00:00", "%Y-%m-%dT%H:%M:%S"), before=None
    )
    existing_obj = await author_repo.list(after_filter)
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_filter_search(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy search filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await author_repo.list(SearchFilter(field_name="name", value="gath", ignore_case=False))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=False))
    # sqlite & mysql are case insensitive by default with a `LIKE`
    dialect = author_repo.session.bind.dialect.name if author_repo.session.bind else "default"
    if dialect in {"sqlite", "mysql"}:
        expected_objs = 1
    else:
        expected_objs = 0
    assert len(existing_obj) == expected_objs
    existing_obj = await author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=True))
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_filter_order_by(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy order by filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await author_repo.list(OrderBy(field_name="created", sort_order="desc"))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await author_repo.list(OrderBy(field_name="created", sort_order="asc"))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_collection(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy collection filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")])
    )
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = await author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2")])
    )
    assert existing_obj[0].name == "Leo Tolstoy"
