"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, insert

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, OrderBy, SearchFilter
from litestar.contrib.sqlalchemy import base
from tests.contrib.sqlalchemy.models import (
    Author,
    AuthorSyncRepository,
    BookSyncRepository,
    Ingredient,
    Store,
    StoreSyncRepository,
)


def seed_db(
    engine: Engine,
    raw_authors: list[dict[str, Any]],
    raw_books: list[dict[str, Any]],
    raw_stores: list[dict[str, Any]],
    raw_ingredients: list[dict[str, Any]],
) -> None:
    """Populate test database with sample data.

    Args:
        engine: The SQLAlchemy engine instance.
    """
    # convert date/time strings to dt objects.
    for raw_author in raw_authors:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d")
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S")
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S")
    for raw_store in raw_stores:
        raw_store["created"] = datetime.strptime(raw_store["created"], "%Y-%m-%dT%H:%M:%S")
        raw_store["updated"] = datetime.strptime(raw_store["updated"], "%Y-%m-%dT%H:%M:%S")
    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)
        conn.execute(insert(Author).values(raw_authors))
        conn.execute(insert(Ingredient).values(raw_ingredients))
        conn.execute(insert(Store).values(raw_stores))


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


def test_repo_count_method(author_repo: AuthorSyncRepository, store_repo: StoreSyncRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    assert author_repo.count() == 2
    assert store_repo.count() == 2


def test_repo_list_and_count_method(
    raw_authors: list[dict[str, Any]],
    author_repo: AuthorSyncRepository,
    raw_stores: list[dict[str, Any]],
    store_repo: StoreSyncRepository,
) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
        raw_stores (list[dict[str, Any]]): list of stores pre-seeded into the mock repository
        store_repo (StoreRepository): The store mock repository
    """
    exp_count = len(raw_authors)
    collection, count = author_repo.list_and_count()
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count

    exp_count2 = len(raw_stores)
    collection2, count2 = store_repo.list_and_count()
    assert exp_count2 == count2
    assert isinstance(collection2, list)
    assert len(collection2) == exp_count2


def test_repo_list_and_count_method_empty(book_repo: BookSyncRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    collection, count = book_repo.list_and_count()
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


def test_repo_list_method(
    raw_authors: list[dict[str, Any]],
    author_repo: AuthorSyncRepository,
    raw_stores: list[dict[str, Any]],
    store_repo: StoreSyncRepository,
) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
        raw_stores (list[dict[str, Any]]): list of stores pre-seeded into the mock repository
        store_repo (StoreRepository): The store mock repository
    """
    exp_count = len(raw_authors)
    collection = author_repo.list()
    assert isinstance(collection, list)
    assert len(collection) == exp_count

    exp_count2 = len(raw_stores)
    collection2 = store_repo.list()
    assert isinstance(collection2, list)
    assert len(collection2) == exp_count2


def test_repo_add_method(
    raw_authors: list[dict[str, Any]],
    author_repo: AuthorSyncRepository,
    raw_stores: list[dict[str, Any]],
    store_repo: StoreSyncRepository,
) -> None:
    """Test SQLALchemy Add.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
        raw_stores (list[dict[str, Any]]): list of stores pre-seeded into the mock repository
        store_repo (StoreRepository): The store mock repository
    """
    exp_count = len(raw_authors) + 1
    new_author = Author(name="Testing", dob=datetime.now())
    obj = author_repo.add(new_author)
    count = author_repo.count()
    assert exp_count == count
    assert isinstance(obj, Author)
    assert new_author.name == obj.name
    assert obj.id is not None

    exp_count2 = len(raw_stores) + 1
    new_store = Store(store_name="Flea Market (Like a Mini Mall) - Montgomery, AL")
    obj2 = store_repo.add(new_store)
    count2 = store_repo.count()
    assert exp_count2 == count2
    assert isinstance(obj2, Store)
    assert new_store.store_name == obj2.store_name
    assert obj2.id is not None
    assert obj2.id > 0


def test_repo_add_many_method(raw_authors: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    exp_count = len(raw_authors) + 2
    objs = author_repo.add_many([Author(name="Testing 2", dob=datetime.now()), Author(name="Cody", dob=datetime.now())])
    count = author_repo.count()
    assert exp_count == count
    assert isinstance(objs, list)
    assert len(objs) == 2
    for obj in objs:
        assert obj.id is not None
        assert obj.name in {"Testing 2", "Cody"}


def test_repo_update_many_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    objs = author_repo.list()
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = author_repo.update_many(objs)
    for obj in objs:
        assert obj.name.startswith("Update")


def test_repo_exists_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    exists = author_repo.exists(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert exists


def test_repo_update_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    obj.name = "Updated Name"
    updated_obj = author_repo.update(obj)
    assert updated_obj.name == obj.name


def test_repo_delete_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = author_repo.delete(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")


def test_repo_delete_many_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete many.

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
    _ = author_repo.add_many(data_to_insert)
    all_objs = author_repo.list()
    ids_to_delete = [existing_obj.id for existing_obj in all_objs]
    objs = author_repo.delete_many(ids_to_delete)
    author_repo.session.commit()
    assert len(objs) > 0
    data, count = author_repo.list_and_count()
    assert data == []
    assert count == 0


def test_repo_get_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.name == "Agatha Christie"


def test_repo_get_one_or_none_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = author_repo.get_one_or_none(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = author_repo.get_one_or_none(name="I don't exist")
    assert none_obj is None


def test_repo_get_one_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    obj = author_repo.get_one(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = author_repo.get_one(name="I don't exist")


def test_repo_get_or_create_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    existing_obj, existing_created = author_repo.get_or_create(name="Agatha Christie")
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_created is False
    new_obj, new_created = author_repo.get_or_create(name="New Author")
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


def test_repo_get_or_create_match_filter(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    now = datetime.now()
    existing_obj, existing_created = author_repo.get_or_create(match_fields="name", name="Agatha Christie", dob=now)
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_obj.dob == now
    assert existing_created is False


def test_repo_upsert_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    existing_obj = author_repo.get_one(name="Agatha Christie")
    existing_obj.name = "Agatha C."
    upsert_update_obj = author_repo.upsert(existing_obj)
    assert upsert_update_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = author_repo.upsert(Author(name="An Author"))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = author_repo.upsert(Author(id=uuid4(), name="Another Author"))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"


def test_repo_filter_before_after(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    before_filter = BeforeAfter(
        field_name="created", before=datetime.strptime("2023-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S"), after=None
    )
    existing_obj = author_repo.list(before_filter)
    existing_obj[0].name = "Leo Tolstoy"

    after_filter = BeforeAfter(
        field_name="created", after=datetime.strptime("2023-03-01T00:00:00", "%Y-%m-%dT%H:%M:%S"), before=None
    )
    existing_obj = author_repo.list(after_filter)
    existing_obj[0].name = "Agatha Christie"


def test_repo_filter_search(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """

    existing_obj = author_repo.list(SearchFilter(field_name="name", value="gath", ignore_case=False))
    existing_obj[0].name = "Agatha Christie"
    existing_obj = author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=False))
    assert len(existing_obj) == 0
    existing_obj = author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=True))
    existing_obj[0].name = "Agatha Christie"


def test_repo_filter_order_by(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """

    existing_obj = author_repo.list(OrderBy(field_name="created", sort_order="desc"))
    existing_obj[0].name = "Agatha Christie"
    existing_obj = author_repo.list(OrderBy(field_name="created", sort_order="asc"))
    existing_obj[0].name = "Leo Tolstoy."


def test_repo_filter_collection(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """

    existing_obj = author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")])
    )
    existing_obj[0].name = "Agatha Christie"

    existing_obj = author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2")])
    )
    existing_obj[0].name = "Leo Tolstoy"
