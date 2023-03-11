from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Mapped

from starlite.contrib.repository.exceptions import ConflictError, RepositoryError
from starlite.contrib.repository.testing.generic_mock_repository import (
    GenericMockRepository,
)
from starlite.contrib.sqlalchemy import base
from tests.contrib.sqlalchemy.models import Author, Book


@pytest.fixture(name="authors")
def fx_authors() -> list[Author]:
    """Collection of Author models."""
    return [
        Author(id=uuid4(), name=name, dob=dob, created=datetime.min, updated=datetime.min)
        for name, dob in [("Agatha Christie", date(1890, 9, 15)), ("Leo Tolstoy", date(1828, 9, 9))]
    ]


@pytest.fixture(name="author_repository_type")
def fx_author_repository_type(
    authors: list[Author], monkeypatch: pytest.MonkeyPatch
) -> type[GenericMockRepository[Author]]:
    """Mock Author repository, pre-seeded with collection data."""
    repo = GenericMockRepository[Author]
    repo.seed_collection(authors)
    return repo


@pytest.fixture(name="author_repository")
def fx_author_repository(
    author_repository_type: type[GenericMockRepository[Author]],
) -> GenericMockRepository[Author]:
    """Mock Author repository instance."""
    return author_repository_type()


async def test_repo_raises_conflict_if_add_with_id(
    authors: list[Author],
    author_repository: GenericMockRepository[Author],
) -> None:
    """Test mock repo raises conflict if add identified entity."""
    with pytest.raises(ConflictError):
        await author_repository.add(authors[0])


def test_generic_mock_repository_parametrization() -> None:
    """Test that the mock repository handles multiple types."""
    author_repo = GenericMockRepository[Author]
    book_repo = GenericMockRepository[Book]
    assert author_repo.model_type is Author  # type:ignore[misc]
    assert book_repo.model_type is Book  # type:ignore[misc]


def test_generic_mock_repository_seed_collection(
    author_repository_type: type[GenericMockRepository[Author]],
) -> None:
    """Test seeding instances."""
    author_repository_type.seed_collection([Author(id="abc")])
    assert "abc" in author_repository_type.collection


def test_generic_mock_repository_clear_collection(
    author_repository_type: type[GenericMockRepository[Author]],
) -> None:
    """Test clearing collection for type."""
    author_repository_type.clear_collection()
    assert not author_repository_type.collection


def test_generic_mock_repository_filter_collection_by_kwargs(
    author_repository: GenericMockRepository[Author],
) -> None:
    """Test filtering the repository collection by kwargs."""
    collection = author_repository.filter_collection_by_kwargs(author_repository.collection, name="Leo Tolstoy")
    assert len(collection) == 1
    assert list(collection.values())[0].name == "Leo Tolstoy"


def test_generic_mock_repository_filter_collection_by_kwargs_and_semantics(
    author_repository: GenericMockRepository[Author],
) -> None:
    """Test that filtering by kwargs has `AND` semantics when multiple kwargs,
    not `OR`."""
    collection = author_repository.filter_collection_by_kwargs(
        author_repository.collection, name="Agatha Christie", dob="1828-09-09"
    )
    assert len(collection) == 0


def test_generic_mock_repository_raises_repository_exception_if_named_attribute_doesnt_exist(
    author_repository: GenericMockRepository[Author],
) -> None:
    """Test that a repo exception is raised if a named attribute doesn't
    exist."""
    with pytest.raises(RepositoryError):
        _ = author_repository.filter_collection_by_kwargs(author_repository.collection, cricket="ball")


async def test_sets_created_updated_on_add() -> None:
    """Test that the repository updates the 'created' and 'updated' timestamps
    if necessary."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    instance = Model()
    assert "created" not in vars(instance)
    assert "updated" not in vars(instance)

    instance = await GenericMockRepository[Model]().add(instance)
    assert "created" in vars(instance)
    assert "updated" in vars(instance)


async def test_sets_updated_on_update(author_repository: GenericMockRepository[Author]) -> None:
    """Test that the repository updates the 'updated' timestamp if
    necessary."""

    instance = list(author_repository.collection.values())[0]
    original_updated = instance.updated
    instance = await author_repository.update(instance)
    assert instance.updated > original_updated


async def test_does_not_set_created_updated() -> None:
    """Test that the repository does not update the 'updated' timestamps when
    appropriate."""

    class Model(base.Base):
        """Inheriting from Base means the model has no created/updated
        timestamp columns."""

        ...

    instance = Model()
    repo = GenericMockRepository[Model]()
    assert "created" not in vars(instance)
    assert "updated" not in vars(instance)
    instance = await repo.add(instance)
    assert "created" not in vars(instance)
    assert "updated" not in vars(instance)
    instance = await repo.update(instance)
    assert "created" not in vars(instance)
    assert "updated" not in vars(instance)


async def test_add() -> None:
    """Test that the repository add method works correctly`."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    instance = Model()

    inserted_instance = await GenericMockRepository[Model]().add(instance)
    assert inserted_instance == instance


async def test_add_many() -> None:
    """Test that the repository add_many method works correctly`."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    instances = [Model(), Model()]

    inserted_instances = await GenericMockRepository[Model]().add_many(instances)
    assert len(instances) == len(inserted_instances)


async def test_update() -> None:
    """Test that the repository update method works correctly`."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericMockRepository[Model]()

    instance = await mock_repo.add(Model(random_column="A"))
    instance.random_column = "B"
    updated_instance = await mock_repo.update(instance)

    assert updated_instance == instance


async def test_update_many() -> None:
    """Test that the repository add_many method works correctly`."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericMockRepository[Model]()
    instances = [Model(random_column="A"), Model(random_column="B")]
    inserted_instances = await mock_repo.add_many(instances)
    for instance in inserted_instances:
        instance.random_column = "C"
    updated_instances = await mock_repo.update_many(instances)
    for instance in updated_instances:
        assert instance.random_column == "C"
    assert len(instances) == len(updated_instances)


async def test_upsert() -> None:
    """Test that the repository upsert method works correctly`."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericMockRepository[Model]()

    instance = await mock_repo.upsert(Model(random_column="A"))
    instance.random_column = "B"
    updated_instance = await mock_repo.upsert(instance)

    assert updated_instance == instance


async def test_list() -> None:
    """Test that the repository list returns records."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many([Model(), Model()])
    listed_instances = await mock_repo.list()
    assert inserted_instances == listed_instances


async def test_delete() -> None:
    """Test that the repository delete functionality."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many([Model(), Model()])
    delete_instance = await mock_repo.delete(inserted_instances[0].id)
    assert delete_instance.id == inserted_instances[0].id
    count = await mock_repo.count()
    assert count == 1


async def test_delete_many() -> None:
    """Test that the repository delete many functionality."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many([Model(), Model()])
    delete_instances = await mock_repo.delete_many([obj.id for obj in inserted_instances])
    assert len(delete_instances) == 2
    count = await mock_repo.count()
    assert count == 0


async def test_list_and_count() -> None:
    """Test that the repository list_and_count returns records and the total record count."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    instances = [Model(), Model()]
    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many(instances)
    listed_instances, count = await mock_repo.list_and_count()
    assert inserted_instances == listed_instances
    assert count == len(instances)


async def test_exists() -> None:
    """Test that the repository exists returns booleans."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericMockRepository[Model]()
    _ = await mock_repo.add_many(instances)
    exists = await mock_repo.exists(random_column="value 1")
    assert exists


async def test_count() -> None:
    """Test that the repository count returns the total record count."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        ...

    instances = [Model(), Model()]
    mock_repo = GenericMockRepository[Model]()
    _ = await mock_repo.add_many(instances)
    count = await mock_repo.count()
    assert count == len(instances)


async def test_get() -> None:
    """Test that the repository get returns a model record correctly."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many(instances)
    item_id = inserted_instances[0].id
    fetched_instance = await mock_repo.get(item_id)
    assert inserted_instances[0] == fetched_instance


async def test_get_one() -> None:
    """Test that the repository get_one returns a model record correctly."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many(instances)
    fetched_instance = await mock_repo.get_one(random_column="value 1")
    assert inserted_instances[0] == fetched_instance
    with pytest.raises(RepositoryError):
        _ = await mock_repo.get_one(random_column="value 3")


async def test_get_one_or_none() -> None:
    """Test that the repository get_one_or_none returns a model record correctly."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many(instances)
    fetched_instance = await mock_repo.get_one_or_none(random_column="value 1")
    assert inserted_instances[0] == fetched_instance
    none_instance = await mock_repo.get_one_or_none(random_column="value 3")
    assert none_instance is None


async def test_get_or_create() -> None:
    """Test that the repository get_or_create returns a model record correctly."""

    class Model(base.AuditBase):
        """Inheriting from AuditBase gives the model 'created' and 'updated'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericMockRepository[Model]()
    inserted_instances = await mock_repo.add_many(instances)
    fetched_instance, fetched_created = await mock_repo.get_or_create(random_column="value 1")
    assert await mock_repo.count() == 2
    assert inserted_instances[0] == fetched_instance
    assert fetched_created is False
    _, created = await mock_repo.get_or_create(random_column="value 3")
    assert await mock_repo.count() == 3
    assert created
