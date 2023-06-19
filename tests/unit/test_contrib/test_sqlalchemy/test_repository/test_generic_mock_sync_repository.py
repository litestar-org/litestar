from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Mapped, mapped_column

from litestar.contrib.repository.exceptions import ConflictError, RepositoryError
from litestar.contrib.repository.testing.generic_mock_repository import (
    GenericSyncMockRepository,
)
from litestar.contrib.sqlalchemy import base
from tests.unit.test_contrib.test_sqlalchemy.models_uuid import UUIDAuthor, UUIDBook


@pytest.fixture(name="authors")
def fx_authors() -> list[UUIDAuthor]:
    """Collection of Author models."""
    return [
        UUIDAuthor(id=uuid4(), name=name, dob=dob, created_at=datetime.min, updated_at=datetime.min)
        for name, dob in [("Agatha Christie", date(1890, 9, 15)), ("Leo Tolstoy", date(1828, 9, 9))]
    ]


@pytest.fixture(name="author_repository_type")
def fx_author_repository_type(
    authors: list[UUIDAuthor], monkeypatch: pytest.MonkeyPatch
) -> type[GenericSyncMockRepository[UUIDAuthor]]:
    """Mock Author repository, pre-seeded with collection data."""
    repo = GenericSyncMockRepository[UUIDAuthor]
    repo.seed_collection(authors)
    return repo


@pytest.fixture(name="author_repository")
def fx_author_repository(
    author_repository_type: type[GenericSyncMockRepository[UUIDAuthor]],
) -> GenericSyncMockRepository[UUIDAuthor]:
    """Mock Author repository instance."""
    return author_repository_type()


async def test_repo_raises_conflict_if_add_with_id(
    authors: list[UUIDAuthor],
    author_repository: GenericSyncMockRepository[UUIDAuthor],
) -> None:
    """Test mock repo raises conflict if add identified entity."""
    with pytest.raises(ConflictError):
        author_repository.add(authors[0])


async def test_repo_raises_conflict_if_add_many_with_id(
    authors: list[UUIDAuthor],
    author_repository: GenericSyncMockRepository[UUIDAuthor],
) -> None:
    """Test mock repo raises conflict if add identified entity."""
    with pytest.raises(ConflictError):
        author_repository.add_many(authors)


def test_generic_mock_repository_parametrization() -> None:
    """Test that the mock repository handles multiple types."""
    author_repo = GenericSyncMockRepository[UUIDAuthor]
    book_repo = GenericSyncMockRepository[UUIDBook]
    assert author_repo.model_type is UUIDAuthor  # type:ignore[misc]
    assert book_repo.model_type is UUIDBook  # type:ignore[misc]


def test_generic_mock_repository_seed_collection(
    author_repository_type: type[GenericSyncMockRepository[UUIDAuthor]],
) -> None:
    """Test seeding instances."""
    author_repository_type.seed_collection([UUIDAuthor(id="abc")])
    assert "abc" in author_repository_type.collection


def test_generic_mock_repository_clear_collection(
    author_repository_type: type[GenericSyncMockRepository[UUIDAuthor]],
) -> None:
    """Test clearing collection for type."""
    author_repository_type.clear_collection()
    assert not author_repository_type.collection


def test_generic_mock_repository_filter_collection_by_kwargs(
    author_repository: GenericSyncMockRepository[UUIDAuthor],
) -> None:
    """Test filtering the repository collection by kwargs."""
    collection = author_repository.filter_collection_by_kwargs(author_repository.collection, name="Leo Tolstoy")
    assert len(collection) == 1
    assert list(collection.values())[0].name == "Leo Tolstoy"


def test_generic_mock_repository_filter_collection_by_kwargs_and_semantics(
    author_repository: GenericSyncMockRepository[UUIDAuthor],
) -> None:
    """Test that filtering by kwargs has `AND` semantics when multiple kwargs,
    not `OR`."""
    collection = author_repository.filter_collection_by_kwargs(
        author_repository.collection, name="Agatha Christie", dob="1828-09-09"
    )
    assert len(collection) == 0


def test_generic_mock_repository_raises_repository_exception_if_named_attribute_doesnt_exist(
    author_repository: GenericSyncMockRepository[UUIDAuthor],
) -> None:
    """Test that a repo exception is raised if a named attribute doesn't
    exist."""
    with pytest.raises(RepositoryError):
        _ = author_repository.filter_collection_by_kwargs(author_repository.collection, cricket="ball")


async def test_sets_created_updated_on_add() -> None:
    """Test that the repository updates the 'created_at' and 'updated_at' timestamps
    if necessary."""

    class UUIDModel(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    uuid_instance = UUIDModel()
    assert "created_at" not in vars(uuid_instance)
    assert "updated_at" not in vars(uuid_instance)

    uuid_instance = GenericSyncMockRepository[UUIDModel]().add(uuid_instance)
    assert "created_at" in vars(uuid_instance)
    assert "updated_at" in vars(uuid_instance)

    bigint_instance = BigIntModel()
    assert "created_at" not in vars(bigint_instance)
    assert "updated_at" not in vars(bigint_instance)

    bigint_instance = GenericSyncMockRepository[BigIntModel]().add(bigint_instance)  # type: ignore[type-var]
    assert "created_at" in vars(bigint_instance)
    assert "updated_at" in vars(bigint_instance)


async def test_sets_updated_on_update(author_repository: GenericSyncMockRepository[UUIDAuthor]) -> None:
    """Test that the repository updates the 'updated' timestamp if
    necessary."""

    instance = list(author_repository.collection.values())[0]
    original_updated = instance.updated_at
    instance = author_repository.update(instance)
    assert instance.updated_at > original_updated


async def test_does_not_set_created_updated() -> None:
    """Test that the repository does not update the 'updated' timestamps when
    appropriate."""

    class UUIDModel(base.UUIDBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    uuid_instance = UUIDModel()
    uuid_repo = GenericSyncMockRepository[UUIDModel]()
    assert "created_at" not in vars(uuid_instance)
    assert "updated_at" not in vars(uuid_instance)
    uuid_instance = uuid_repo.add(uuid_instance)
    assert "created_at" not in vars(uuid_instance)
    assert "updated_at" not in vars(uuid_instance)
    uuid_instance = uuid_repo.update(uuid_instance)
    assert "created_at" not in vars(uuid_instance)
    assert "updated_at" not in vars(uuid_instance)

    bigint_instance = BigIntModel()
    bigint_repo = GenericSyncMockRepository[BigIntModel]()  # type: ignore[type-var]
    assert "created_at" not in vars(bigint_instance)
    assert "updated_at" not in vars(bigint_instance)
    bigint_instance = bigint_repo.add(bigint_instance)
    assert "created_at" not in vars(bigint_instance)
    assert "updated_at" not in vars(bigint_instance)
    bigint_instance = bigint_repo.update(bigint_instance)
    assert "created_at" not in vars(bigint_instance)
    assert "updated_at" not in vars(bigint_instance)


async def test_add() -> None:
    """Test that the repository add method works correctly`."""

    class UUIDModel(base.UUIDBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    uuid_instance = UUIDModel()

    inserted_uuid_instance = GenericSyncMockRepository[UUIDModel]().add(uuid_instance)
    assert inserted_uuid_instance == uuid_instance

    bigint_instance = BigIntModel()

    inserted_bigint_instance = GenericSyncMockRepository[BigIntModel]().add(bigint_instance)  # type: ignore[type-var]
    assert inserted_bigint_instance == bigint_instance


async def test_add_many() -> None:
    """Test that the repository add_many method works correctly`."""

    class UUIDModel(base.UUIDBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    uuid_instances = [UUIDModel(), UUIDModel()]
    bigint_instance = [BigIntModel(), BigIntModel()]

    inserted_uuid_instances = GenericSyncMockRepository[UUIDModel]().add_many(uuid_instances)
    inserted_bigint_instance = GenericSyncMockRepository[BigIntModel]().add_many(bigint_instance)  # type: ignore[type-var]

    assert len(uuid_instances) == len(inserted_uuid_instances)
    assert len(bigint_instance) == len(inserted_bigint_instance)


async def test_update() -> None:
    """Test that the repository update method works correctly`."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericSyncMockRepository[Model]()

    instance = mock_repo.add(Model(random_column="A"))
    instance.random_column = "B"
    updated_instance = mock_repo.update(instance)

    assert updated_instance == instance


async def test_update_many() -> None:
    """Test that the repository add_many method works correctly`."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericSyncMockRepository[Model]()
    instances = [Model(random_column="A"), Model(random_column="B")]
    inserted_instances = mock_repo.add_many(instances)
    for instance in inserted_instances:
        instance.random_column = "C"
    updated_instances = mock_repo.update_many(instances)
    for instance in updated_instances:
        assert instance.random_column == "C"
    assert len(instances) == len(updated_instances)


async def test_upsert() -> None:
    """Test that the repository upsert method works correctly`."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    mock_repo = GenericSyncMockRepository[Model]()

    instance = mock_repo.upsert(Model(random_column="A"))
    instance.random_column = "B"
    updated_instance = mock_repo.upsert(instance)

    assert updated_instance == instance


async def test_list() -> None:
    """Test that the repository list returns records."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many([Model(), Model()])
    listed_instances = mock_repo.list()
    assert inserted_instances == listed_instances


async def test_delete() -> None:
    """Test that the repository delete functionality."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many([Model(), Model()])
    delete_instance = mock_repo.delete(inserted_instances[0].id)
    assert delete_instance.id == inserted_instances[0].id
    count = mock_repo.count()
    assert count == 1


async def test_delete_many() -> None:
    """Test that the repository delete many functionality."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many([Model(), Model()])
    delete_instances = mock_repo.delete_many([obj.id for obj in inserted_instances])
    assert len(delete_instances) == 2
    count = mock_repo.count()
    assert count == 0


async def test_list_and_count() -> None:
    """Test that the repository list_and_count returns records and the total record count."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    instances = [Model(), Model()]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    listed_instances, count = mock_repo.list_and_count()
    assert inserted_instances == listed_instances
    assert count == len(instances)


async def test_exists() -> None:
    """Test that the repository exists returns booleans."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    _ = mock_repo.add_many(instances)
    exists = mock_repo.exists(random_column="value 1")
    assert exists


async def test_count() -> None:
    """Test that the repository count returns the total record count."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    instances = [Model(), Model()]
    mock_repo = GenericSyncMockRepository[Model]()
    _ = mock_repo.add_many(instances)
    count = mock_repo.count()
    assert count == len(instances)


async def test_get() -> None:
    """Test that the repository get returns a model record correctly."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    item_id = inserted_instances[0].id
    fetched_instance = mock_repo.get(item_id)
    assert inserted_instances[0] == fetched_instance


async def test_get_one() -> None:
    """Test that the repository get_one returns a model record correctly."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    fetched_instance = mock_repo.get_one(random_column="value 1")
    assert inserted_instances[0] == fetched_instance
    with pytest.raises(RepositoryError):
        _ = mock_repo.get_one(random_column="value 3")


async def test_get_one_or_none() -> None:
    """Test that the repository get_one_or_none returns a model record correctly."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]

    instances = [Model(random_column="value 1"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    fetched_instance = mock_repo.get_one_or_none(random_column="value 1")
    assert inserted_instances[0] == fetched_instance
    none_instance = mock_repo.get_one_or_none(random_column="value 3")
    assert none_instance is None


async def test_get_or_create() -> None:
    """Test that the repository get_or_create returns a model record correctly."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]
        cool_attribute: Mapped[str] = mapped_column(nullable=True)  # pyright: ignore

    instances = [Model(random_column="value 1", cool_attribute="yep"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    fetched_instance, fetched_created = mock_repo.get_or_create(random_column="value 2")
    assert mock_repo.count() == 2
    assert inserted_instances[1] == fetched_instance
    assert fetched_created is False
    _, created = mock_repo.get_or_create(random_column="value 3")
    assert mock_repo.count() == 3
    assert created


async def test_get_or_create_match_fields() -> None:
    """Test that the repository get_or_create returns a model record correctly."""

    class Model(base.UUIDAuditBase):
        """Inheriting from AuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        random_column: Mapped[str]
        cool_attribute: Mapped[str] = mapped_column(nullable=True)  # pyright: ignore

    instances = [Model(random_column="value 1", cool_attribute="yep"), Model(random_column="value 2")]
    mock_repo = GenericSyncMockRepository[Model]()
    inserted_instances = mock_repo.add_many(instances)
    fetched_instance, fetched_created = mock_repo.get_or_create(
        match_fields=["random_column"], random_column="value 1", cool_attribute="other thing"
    )
    assert mock_repo.count() == 2
    assert inserted_instances[0] == fetched_instance
    assert fetched_created is False
