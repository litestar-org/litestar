"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Iterator, List, Literal, Type, Union, cast
from uuid import UUID

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_lazyfixture import lazy_fixture
from sqlalchemy import Engine, Table, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    NotInCollectionFilter,
    NotInSearchFilter,
    OnBeforeAfter,
    OrderBy,
    SearchFilter,
)
from litestar.contrib.sqlalchemy import base
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository
from tests.helpers import maybe_async
from tests.unit.test_contrib.test_sqlalchemy import models_bigint, models_uuid

from .helpers import update_raw_records

RepositoryPKType = Literal["uuid", "bigint"]
AuthorModel = Type[Union[models_uuid.UUIDAuthor, models_bigint.BigIntAuthor]]
RuleModel = Type[Union[models_uuid.UUIDRule, models_bigint.BigIntRule]]
ModelWithFetchedValue = Type[Union[models_uuid.UUIDModelWithFetchedValue, models_bigint.BigIntModelWithFetchedValue]]
ItemModel = Type[Union[models_uuid.UUIDItem, models_bigint.BigIntItem]]
TagModel = Type[Union[models_uuid.UUIDTag, models_bigint.BigIntTag]]

AnyAuthor = Union[models_uuid.UUIDAuthor, models_bigint.BigIntAuthor]
AuthorRepository = SQLAlchemyAsyncRepository[AnyAuthor]

AnyRule = Union[models_uuid.UUIDRule, models_bigint.BigIntRule]
RuleRepository = SQLAlchemyAsyncRepository[AnyRule]

AnyBook = Union[models_uuid.UUIDBook, models_bigint.BigIntBook]
BookRepository = SQLAlchemyAsyncRepository[AnyBook]

AnyTag = Union[models_uuid.UUIDTag, models_bigint.BigIntTag]
TagRepository = SQLAlchemyAsyncRepository[AnyTag]

AnyItem = Union[models_uuid.UUIDItem, models_bigint.BigIntItem]
ItemRepository = SQLAlchemyAsyncRepository[AnyItem]

AnyModelWithFetchedValue = Union[models_uuid.UUIDModelWithFetchedValue, models_bigint.BigIntModelWithFetchedValue]
ModelWithFetchedValueRepository = SQLAlchemyAsyncRepository[AnyModelWithFetchedValue]

RawRecordData = List[Dict[str, Any]]


@pytest.fixture(name="raw_authors_uuid")
def fx_raw_authors_uuid() -> RawRecordData:
    """Unstructured author representations."""
    return [
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created_at": "2023-05-01T00:00:00",
            "updated_at": "2023-05-11T00:00:00",
        },
        {
            "id": UUID("5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2"),
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created_at": "2023-03-01T00:00:00",
            "updated_at": "2023-05-15T00:00:00",
        },
    ]


@pytest.fixture(name="raw_books_uuid")
def fx_raw_books_uuid(raw_authors_uuid: RawRecordData) -> RawRecordData:
    """Unstructured book representations."""
    return [
        {
            "id": UUID("f34545b9-663c-4fce-915d-dd1ae9cea42a"),
            "title": "Murder on the Orient Express",
            "author_id": raw_authors_uuid[0]["id"],
            "author": raw_authors_uuid[0],
        },
    ]


@pytest.fixture(name="raw_log_events_uuid")
def fx_raw_log_events_uuid() -> RawRecordData:
    """Unstructured log events representations."""
    return [
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea42a",
            "logged_at": "0001-01-01T00:00:00",
            "payload": {"foo": "bar", "baz": datetime.now()},
            "created_at": "0001-01-01T00:00:00",
            "updated_at": "0001-01-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_rules_uuid")
def fx_raw_rules_uuid() -> RawRecordData:
    """Unstructured rules representations."""
    return [
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea42a",
            "name": "Initial loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "setting_123": 1}),
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-02-01T00:00:00",
        },
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea34b",
            "name": "Secondary loading rule.",
            "config": {"url": "https://litestar.dev", "bar": "foo", "setting_123": 4},
            "created_at": "2023-02-01T00:00:00",
            "updated_at": "2023-02-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_authors_bigint")
def fx_raw_authors_bigint() -> RawRecordData:
    """Unstructured author representations."""
    return [
        {
            "id": 2023,
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created_at": "2023-05-01T00:00:00",
            "updated_at": "2023-05-11T00:00:00",
        },
        {
            "id": 2024,
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created_at": "2023-03-01T00:00:00",
            "updated_at": "2023-05-15T00:00:00",
        },
    ]


@pytest.fixture(name="raw_books_bigint")
def fx_raw_books_bigint(raw_authors_bigint: RawRecordData) -> RawRecordData:
    """Unstructured book representations."""
    return [
        {
            "title": "Murder on the Orient Express",
            "author_id": raw_authors_bigint[0]["id"],
            "author": raw_authors_bigint[0],
        },
    ]


@pytest.fixture(name="raw_log_events_bigint")
def fx_raw_log_events_bigint() -> RawRecordData:
    """Unstructured log events representations."""
    return [
        {
            "id": 2025,
            "logged_at": "0001-01-01T00:00:00",
            "payload": {"foo": "bar", "baz": datetime.now()},
            "created_at": "0001-01-01T00:00:00",
            "updated_at": "0001-01-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_rules_bigint")
def fx_raw_rules_bigint() -> RawRecordData:
    """Unstructured rules representations."""
    return [
        {
            "id": 2025,
            "name": "Initial loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "setting_123": 1}),
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-02-01T00:00:00",
        },
        {
            "id": 2024,
            "name": "Secondary loading rule.",
            "config": {"url": "https://litestar.dev", "bar": "foo", "setting_123": 4},
            "created_at": "2023-02-01T00:00:00",
            "updated_at": "2023-02-01T00:00:00",
        },
    ]


@pytest.fixture(params=["uuid", "bigint"])
def repository_pk_type(request: FixtureRequest) -> RepositoryPKType:
    """Return the primary key type of the repository"""
    return cast(RepositoryPKType, request.param)


@pytest.fixture()
def author_model(repository_pk_type: RepositoryPKType) -> AuthorModel:
    """Return the ``Author`` model matching the current repository PK type"""
    if repository_pk_type == "uuid":
        return models_uuid.UUIDAuthor
    return models_bigint.BigIntAuthor


@pytest.fixture()
def rule_model(repository_pk_type: RepositoryPKType) -> RuleModel:
    """Return the ``Rule`` model matching the current repository PK type"""
    if repository_pk_type == "bigint":
        return models_bigint.BigIntRule
    return models_uuid.UUIDRule


@pytest.fixture()
def model_with_fetched_value(repository_pk_type: RepositoryPKType) -> ModelWithFetchedValue:
    """Return the ``ModelWithFetchedValue`` model matching the current repository PK type"""
    if repository_pk_type == "bigint":
        return models_bigint.BigIntModelWithFetchedValue
    return models_uuid.UUIDModelWithFetchedValue


@pytest.fixture()
def item_model(repository_pk_type: RepositoryPKType) -> ItemModel:
    """Return the ``Item`` model matching the current repository PK type"""
    if repository_pk_type == "bigint":
        return models_bigint.BigIntItem
    return models_uuid.UUIDItem


@pytest.fixture()
def tag_model(repository_pk_type: RepositoryPKType) -> TagModel:
    """Return the ``Tag`` model matching the current repository PK type"""
    if repository_pk_type == "uuid":
        return models_uuid.UUIDTag
    return models_bigint.BigIntTag


@pytest.fixture()
def book_model(repository_pk_type: RepositoryPKType) -> type[models_uuid.UUIDBook | models_bigint.BigIntBook]:
    """Return the ``Book`` model matching the current repository PK type"""
    if repository_pk_type == "uuid":
        return models_uuid.UUIDBook
    return models_bigint.BigIntBook


@pytest.fixture()
def new_pk_id(repository_pk_type: RepositoryPKType) -> Any:
    """Return an unused primary key, matching the current repository PK type"""
    if repository_pk_type == "uuid":
        return UUID("baa0a5c7-5404-4821-bc76-6cf5e73c8219")
    return 10


@pytest.fixture()
def existing_author_ids(raw_authors: RawRecordData) -> Iterator[Any]:
    """Return the existing primary keys based on the raw data provided"""
    return (author["id"] for author in raw_authors)


@pytest.fixture()
def first_author_id(raw_authors: RawRecordData) -> Any:
    """Return the primary key of the first ``Author`` record of the current repository PK type"""
    return raw_authors[0]["id"]


@pytest.fixture(
    params=[
        pytest.param("sqlite_engine", marks=pytest.mark.sqlalchemy_sqlite),
        pytest.param(
            "duckdb_engine",
            marks=[
                pytest.mark.sqlalchemy_duckdb,
                pytest.mark.sqlalchemy_integration,
                pytest.mark.xdist_group("duckdb"),
            ],
        ),
        pytest.param(
            "oracle_engine",
            marks=[
                pytest.mark.sqlalchemy_oracledb,
                pytest.mark.sqlalchemy_integration,
                pytest.mark.xdist_group("oracle"),
            ],
        ),
        pytest.param(
            "psycopg_engine",
            marks=[
                pytest.mark.sqlalchemy_psycopg_sync,
                pytest.mark.sqlalchemy_integration,
                pytest.mark.xdist_group("postgres"),
            ],
        ),
        pytest.param(
            "spanner_engine",
            marks=[
                pytest.mark.sqlalchemy_spanner,
                pytest.mark.sqlalchemy_integration,
                pytest.mark.xdist_group("spanner"),
            ],
        ),
    ]
)
def engine(request: FixtureRequest, repository_pk_type: RepositoryPKType) -> Engine:
    """Return a synchronous engine. Parametrized to return all engines supported by
    the repository PK type"""
    engine = cast(Engine, request.getfixturevalue(request.param))
    if engine.dialect.name.startswith("spanner") and repository_pk_type == "bigint":
        pytest.skip(reason="Spanner does not support integer based primary keys")
    return engine


@pytest.fixture()
def raw_authors(request: FixtureRequest, repository_pk_type: RepositoryPKType) -> RawRecordData:
    """Return raw ``Author`` data matching the current PK type"""
    if repository_pk_type == "bigint":
        authors = request.getfixturevalue("raw_authors_bigint")
    else:
        authors = request.getfixturevalue("raw_authors_uuid")
    return cast("RawRecordData", authors)


@pytest.fixture()
def raw_rules(request: FixtureRequest, repository_pk_type: RepositoryPKType) -> RawRecordData:
    """Return raw ``Rule`` data matching the current PK type"""
    if repository_pk_type == "bigint":
        rules = request.getfixturevalue("raw_rules_bigint")
    else:
        rules = request.getfixturevalue("raw_rules_uuid")
    return cast("RawRecordData", rules)


def _seed_db_sync(
    *,
    engine: Engine,
    raw_authors: RawRecordData,
    raw_rules: RawRecordData,
    author_model: AuthorModel,
    rule_model: RuleModel,
) -> None:
    update_raw_records(raw_authors=raw_authors, raw_rules=raw_rules)

    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)

    with engine.begin() as conn:
        for author in raw_authors:
            conn.execute(insert(author_model).values(author))
        for rule in raw_rules:
            conn.execute(insert(rule_model).values(rule))


def _seed_spanner(
    *,
    engine: Engine,
    raw_authors_uuid: RawRecordData,
    raw_rules_uuid: RawRecordData,
) -> list[Table]:
    update_raw_records(raw_authors=raw_authors_uuid, raw_rules=raw_rules_uuid)

    with engine.begin() as txn:
        objs = [
            tbl for tbl in models_uuid.UUIDAuthor.registry.metadata.sorted_tables if tbl.description.startswith("uuid")
        ]
        models_uuid.UUIDAuthor.registry.metadata.create_all(txn, tables=objs)
    return objs


@pytest.fixture()
def seed_db_sync(
    engine: Engine,
    raw_authors: RawRecordData,
    raw_rules: RawRecordData,
    author_model: AuthorModel,
    rule_model: RuleModel,
) -> None:
    if engine.dialect.name.startswith("spanner"):
        _seed_spanner(engine=engine, raw_authors_uuid=raw_authors, raw_rules_uuid=raw_rules)
    else:
        _seed_db_sync(
            engine=engine,
            raw_authors=raw_authors,
            raw_rules=raw_rules,
            author_model=author_model,
            rule_model=rule_model,
        )


@pytest.fixture()
def session(
    engine: Engine,
    raw_authors: RawRecordData,
    raw_rules: RawRecordData,
    seed_db_sync: None,
) -> Generator[Session, None, None]:
    """Return a synchronous session for the current engine"""
    session = sessionmaker(bind=engine)()

    if engine.dialect.name.startswith("spanner"):
        try:
            author_repo = models_uuid.AuthorSyncRepository(session=session)
            for author in raw_authors:
                _ = author_repo.get_or_create(match_fields="name", **author)
            if not bool(os.environ.get("SPANNER_EMULATOR_HOST")):
                rule_repo = models_uuid.RuleSyncRepository(session=session)
                for rule in raw_rules:
                    _ = rule_repo.add(models_uuid.UUIDRule(**rule))
            yield session
        finally:
            session.rollback()
            session.close()
        with engine.begin() as txn:
            models_uuid.UUIDAuthor.registry.metadata.drop_all(txn, tables=seed_db_sync)
    else:
        try:
            yield session
        finally:
            session.rollback()
            session.close()


@pytest.fixture()
async def seed_db_async(
    async_engine: AsyncEngine,
    raw_authors: RawRecordData,
    raw_rules: RawRecordData,
    author_model: AuthorModel,
    rule_model: RuleModel,
) -> None:
    """Return an asynchronous session for the current engine"""

    # convert date/time strings to dt objects.
    for raw_author in raw_authors:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created_at"] = datetime.strptime(raw_author["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
        raw_author["updated_at"] = datetime.strptime(raw_author["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
    for raw_author in raw_rules:
        raw_author["created_at"] = datetime.strptime(raw_author["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
        raw_author["updated_at"] = datetime.strptime(raw_author["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )

    async with async_engine.begin() as conn:
        await conn.run_sync(base.orm_registry.metadata.drop_all)
        await conn.run_sync(base.orm_registry.metadata.create_all)
        await conn.execute(insert(author_model).values(raw_authors))
        await conn.execute(insert(rule_model).values(raw_rules))


@pytest.fixture(params=[lazy_fixture("session"), lazy_fixture("async_session")], ids=["sync", "async"])
def any_session(request: FixtureRequest) -> AsyncSession | Session:
    """Return a session for the current session"""
    if isinstance(request.param, AsyncSession):
        request.getfixturevalue("seed_db_async")
    else:
        request.getfixturevalue("seed_db_sync")
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def repository_module(repository_pk_type: RepositoryPKType) -> Any:
    return models_uuid if repository_pk_type == "uuid" else models_bigint


@pytest.fixture()
def author_repo(any_session: AsyncSession | Session, repository_module: Any) -> AuthorRepository:
    """Return an AuthorAsyncRepository or AuthorSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.AuthorAsyncRepository(session=any_session)
    else:
        repo = repository_module.AuthorSyncRepository(session=any_session)
    return cast(AuthorRepository, repo)


@pytest.fixture()
def rule_repo(any_session: AsyncSession | Session, repository_module: Any) -> RuleRepository:
    """Return an RuleAsyncRepository or RuleSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.RuleAsyncRepository(session=any_session)
    else:
        repo = repository_module.RuleSyncRepository(session=any_session)
    return cast(RuleRepository, repo)


@pytest.fixture()
def book_repo(any_session: AsyncSession | Session, repository_module: Any) -> BookRepository:
    """Return an BookAsyncRepository or BookSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.BookAsyncRepository(session=any_session)
    else:
        repo = repository_module.BookSyncRepository(session=any_session)
    return cast(BookRepository, repo)


@pytest.fixture()
def tag_repo(any_session: AsyncSession | Session, repository_module: Any) -> ItemRepository:
    """Return an TagAsyncRepository or TagSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.TagAsyncRepository(session=any_session)
    else:
        repo = repository_module.TagSyncRepository(session=any_session)

    return cast(ItemRepository, repo)


@pytest.fixture()
def item_repo(any_session: AsyncSession | Session, repository_module: Any) -> ItemRepository:
    """Return an ItemAsyncRepository or ItemSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ItemAsyncRepository(session=any_session)
    else:
        repo = repository_module.ItemSyncRepository(session=any_session)

    return cast(ItemRepository, repo)


@pytest.fixture()
def model_with_fetched_value_repo(
    any_session: AsyncSession | Session, repository_module: Any
) -> ModelWithFetchedValueRepository:
    """Return an ModelWithFetchedValueAsyncRepository or ModelWithFetchedValueSyncRepository
    based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ModelWithFetchedValueAsyncRepository(session=any_session)
    else:
        repo = repository_module.ModelWithFetchedValueSyncRepository(session=any_session)
    return cast(ModelWithFetchedValueRepository, repo)


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorRepository) -> None:
    """Test SQLAlchemy filter by kwargs with invalid column name.

    Args:
        author_repo: The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


async def test_repo_count_method(author_repo: AuthorRepository) -> None:
    """Test SQLAlchemy count.

    Args:
        author_repo: The author mock repository
    """
    assert await maybe_async(author_repo.count()) == 2


async def test_repo_list_and_count_method(raw_authors: RawRecordData, author_repo: AuthorRepository) -> None:
    """Test SQLAlchemy list with count in asyncpg.

    Args:
        raw_authors: list of authors pre-seeded into the mock repository
        author_repo: The author mock repository
    """
    exp_count = len(raw_authors)
    collection, count = await maybe_async(author_repo.list_and_count())
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_list_and_count_method_empty(book_repo: BookRepository) -> None:
    collection, count = await maybe_async(book_repo.list_and_count())
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


async def test_repo_created_updated(
    author_repo: AuthorRepository, book_model: type[AnyBook], repository_pk_type: RepositoryPKType
) -> None:
    author = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    assert author.created_at is not None
    assert author.updated_at is not None
    original_update_dt = author.updated_at

    # looks odd, but we want to get correct type checking here
    if repository_pk_type == "uuid":
        author = cast(models_uuid.UUIDAuthor, author)
        book_model = cast("type[models_uuid.UUIDBook]", book_model)
    else:
        author = cast(models_bigint.BigIntAuthor, author)
        book_model = cast("type[models_bigint.BigIntBook]", book_model)
    author.books.append(book_model(title="Testing"))  # type: ignore[arg-type]
    author = await maybe_async(author_repo.update(author))
    assert author.updated_at > original_update_dt


async def test_repo_list_method(
    raw_authors_uuid: RawRecordData,
    author_repo: AuthorRepository,
) -> None:
    exp_count = len(raw_authors_uuid)
    collection = await maybe_async(author_repo.list())
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_add_method(
    raw_authors: RawRecordData, author_repo: AuthorRepository, author_model: AuthorModel
) -> None:
    exp_count = len(raw_authors) + 1
    new_author = author_model(name="Testing", dob=datetime.now().date())
    obj = await maybe_async(author_repo.add(new_author))
    count = await maybe_async(author_repo.count())
    assert exp_count == count
    assert isinstance(obj, author_model)
    assert new_author.name == obj.name
    assert obj.id is not None


async def test_repo_add_many_method(
    raw_authors: RawRecordData, author_repo: AuthorRepository, author_model: AuthorModel
) -> None:
    exp_count = len(raw_authors) + 2
    objs = await maybe_async(
        author_repo.add_many(
            [
                author_model(name="Testing 2", dob=datetime.now().date()),
                author_model(name="Cody", dob=datetime.now().date()),
            ]
        )
    )
    count = await maybe_async(author_repo.count())
    assert exp_count == count
    assert isinstance(objs, list)
    assert len(objs) == 2
    for obj in objs:
        assert obj.id is not None
        assert obj.name in {"Testing 2", "Cody"}


async def test_repo_update_many_method(author_repo: AuthorRepository) -> None:
    if author_repo._dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    objs = await maybe_async(author_repo.list())
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = await maybe_async(author_repo.update_many(objs))
    for obj in objs:
        assert obj.name.startswith("Update")


async def test_repo_exists_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    exists = await maybe_async(author_repo.exists(id=first_author_id))
    assert exists


async def test_repo_update_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    obj = await maybe_async(author_repo.get(first_author_id))
    obj.name = "Updated Name"
    updated_obj = await maybe_async(author_repo.update(obj))
    assert updated_obj.name == obj.name


async def test_repo_delete_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    obj = await maybe_async(author_repo.delete(first_author_id))
    assert obj.id == first_author_id


async def test_repo_delete_many_method(author_repo: AuthorRepository, author_model: AuthorModel) -> None:
    data_to_insert = [author_model(name="author name %d" % chunk) for chunk in range(2000)]
    _ = await maybe_async(author_repo.add_many(data_to_insert))
    all_objs = await maybe_async(author_repo.list())
    ids_to_delete = [existing_obj.id for existing_obj in all_objs]
    objs = await maybe_async(author_repo.delete_many(ids_to_delete))
    await maybe_async(author_repo.session.commit())
    assert len(objs) > 0
    data, count = await maybe_async(author_repo.list_and_count())
    assert data == []
    assert count == 0


async def test_repo_get_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    obj = await maybe_async(author_repo.get(first_author_id))
    assert obj.name == "Agatha Christie"


async def test_repo_get_one_or_none_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    obj = await maybe_async(author_repo.get_one_or_none(id=first_author_id))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await maybe_async(author_repo.get_one_or_none(name="I don't exist"))
    assert none_obj is None


async def test_repo_get_one_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    obj = await maybe_async(author_repo.get_one(id=first_author_id))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await author_repo.get_one(name="I don't exist")


async def test_repo_get_or_create_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    existing_obj, existing_created = await maybe_async(author_repo.get_or_create(name="Agatha Christie"))
    assert existing_obj.id == first_author_id
    assert existing_created is False
    new_obj, new_created = await maybe_async(author_repo.get_or_create(name="New Author"))
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


async def test_repo_get_or_create_match_filter(author_repo: AuthorRepository, first_author_id: Any) -> None:
    now = datetime.now()
    existing_obj, existing_created = await maybe_async(
        author_repo.get_or_create(match_fields="name", name="Agatha Christie", dob=now.date())
    )
    assert existing_obj.id == first_author_id
    assert existing_obj.dob == now.date()
    assert existing_created is False


async def test_repo_upsert_method(
    author_repo: AuthorRepository, first_author_id: Any, author_model: AuthorModel, new_pk_id: Any
) -> None:
    existing_obj = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    existing_obj.name = "Agatha C."
    upsert_update_obj = await maybe_async(author_repo.upsert(existing_obj))
    assert upsert_update_obj.id == first_author_id
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = await maybe_async(author_repo.upsert(author_model(name="An Author")))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = await maybe_async(author_repo.upsert(author_model(id=new_pk_id, name="Another Author")))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"


async def test_repo_upsert_many_method(
    author_repo: AuthorRepository, existing_author_ids: Generator[Any, None, None], author_model: AuthorModel
) -> None:
    first_author_id = next(existing_author_ids)
    second_author_id = next(existing_author_ids)
    existing_obj = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    existing_obj.name = "Agatha C."
    upsert_update_objs = await maybe_async(
        author_repo.upsert_many(
            [
                existing_obj,
                author_model(id=second_author_id, name="Inserted Author"),
                author_model(name="Custom Author"),
            ]
        )
    )
    assert len(upsert_update_objs) == 3
    assert upsert_update_objs[0].id == first_author_id
    assert upsert_update_objs[0].name == "Agatha C."
    assert upsert_update_objs[1].id == second_author_id
    assert upsert_update_objs[1].name == "Inserted Author"
    assert upsert_update_objs[2].id is not None
    assert upsert_update_objs[2].name == "Custom Author"


async def test_repo_filter_before_after(author_repo: AuthorRepository) -> None:
    before_filter = BeforeAfter(
        field_name="created_at",
        before=datetime.strptime("2023-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        after=None,
    )
    existing_obj = await maybe_async(author_repo.list(before_filter))
    assert existing_obj[0].name == "Leo Tolstoy"

    after_filter = BeforeAfter(
        field_name="created_at",
        after=datetime.strptime("2023-03-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        before=None,
    )
    existing_obj = await maybe_async(author_repo.list(after_filter))
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_filter_on_before_after(author_repo: AuthorRepository) -> None:
    before_filter = OnBeforeAfter(
        field_name="created_at",
        on_or_before=datetime.strptime("2023-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        on_or_after=None,
    )
    existing_obj = await maybe_async(
        author_repo.list(*[before_filter, OrderBy(field_name="created_at", sort_order="desc")])  # type: ignore
    )
    assert existing_obj[0].name == "Agatha Christie"

    after_filter = OnBeforeAfter(
        field_name="created_at",
        on_or_after=datetime.strptime("2023-03-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        on_or_before=None,
    )
    existing_obj = await maybe_async(
        author_repo.list(*[after_filter, OrderBy(field_name="created_at", sort_order="desc")])  # type: ignore
    )
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_filter_search(author_repo: AuthorRepository) -> None:
    existing_obj = await maybe_async(author_repo.list(SearchFilter(field_name="name", value="gath", ignore_case=False)))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await maybe_async(author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=False)))
    # sqlite & mysql are case insensitive by default with a `LIKE`
    dialect = author_repo.session.bind.dialect.name if author_repo.session.bind else "default"
    expected_objs = 1 if dialect in {"sqlite", "mysql"} else 0
    assert len(existing_obj) == expected_objs
    existing_obj = await maybe_async(author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=True)))
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_filter_not_in_search(author_repo: AuthorRepository) -> None:
    existing_obj = await maybe_async(
        author_repo.list(NotInSearchFilter(field_name="name", value="gath", ignore_case=False))
    )
    assert existing_obj[0].name == "Leo Tolstoy"
    existing_obj = await maybe_async(
        author_repo.list(NotInSearchFilter(field_name="name", value="GATH", ignore_case=False))
    )
    # sqlite & mysql are case insensitive by default with a `LIKE`
    dialect = author_repo.session.bind.dialect.name if author_repo.session.bind else "default"
    expected_objs = 1 if dialect in {"sqlite", "mysql"} else 2
    assert len(existing_obj) == expected_objs
    existing_obj = await maybe_async(
        author_repo.list(NotInSearchFilter(field_name="name", value="GATH", ignore_case=True))
    )
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_order_by(author_repo: AuthorRepository) -> None:
    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="desc")))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="asc")))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_collection(
    author_repo: AuthorRepository, existing_author_ids: Generator[Any, None, None]
) -> None:
    first_author_id = next(existing_author_ids)
    second_author_id = next(existing_author_ids)
    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[first_author_id])))
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[second_author_id])))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_not_in_collection(
    author_repo: AuthorRepository, existing_author_ids: Generator[Any, None, None]
) -> None:
    first_author_id = next(existing_author_ids)
    second_author_id = next(existing_author_ids)
    existing_obj = await maybe_async(author_repo.list(NotInCollectionFilter(field_name="id", values=[first_author_id])))
    assert existing_obj[0].name == "Leo Tolstoy"

    existing_obj = await maybe_async(
        author_repo.list(NotInCollectionFilter(field_name="id", values=[second_author_id]))
    )
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_json_methods(
    raw_rules_uuid: RawRecordData, rule_repo: RuleRepository, rule_model: RuleModel
) -> None:
    if rule_repo._dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    exp_count = len(raw_rules_uuid) + 1
    new_rule = rule_model(name="Testing", config={"an": "object"})
    obj = await maybe_async(rule_repo.add(new_rule))
    count = await maybe_async(rule_repo.count())
    assert exp_count == count
    assert isinstance(obj, rule_model)
    assert new_rule.name == obj.name
    assert new_rule.config == obj.config
    assert obj.id is not None
    obj.config = {"the": "update"}
    updated = await maybe_async(rule_repo.update(obj))
    assert obj.config == updated.config

    get_obj, get_created = await maybe_async(
        rule_repo.get_or_create(match_fields=["name"], name="Secondary loading rule.", config={"another": "object"})
    )
    assert get_created is False
    assert get_obj.id is not None
    assert get_obj.config == {"another": "object"}

    new_obj, new_created = await maybe_async(
        rule_repo.get_or_create(match_fields=["name"], name="New rule.", config={"new": "object"})
    )
    assert new_created is True
    assert new_obj.id is not None
    assert new_obj.config == {"new": "object"}


async def test_repo_fetched_value(
    model_with_fetched_value_repo: ModelWithFetchedValueRepository, model_with_fetched_value: ModelWithFetchedValue
) -> None:
    obj = await maybe_async(model_with_fetched_value_repo.add(model_with_fetched_value(val=1)))
    first_time = obj.updated
    assert first_time is not None
    assert obj.val == 1
    await maybe_async(model_with_fetched_value_repo.session.commit())
    await maybe_async(asyncio.sleep(2))
    obj.val = 2
    obj = await maybe_async(model_with_fetched_value_repo.update(obj))
    assert obj.updated is not None
    assert obj.val == 2
    assert obj.updated != first_time


async def test_lazy_load(
    item_repo: ItemRepository, tag_repo: TagRepository, item_model: ItemModel, tag_model: TagModel
) -> None:
    tag_obj = await maybe_async(tag_repo.add(tag_model(name="A new tag")))
    assert tag_obj
    new_items = await maybe_async(
        item_repo.add_many([item_model(name="The first item"), item_model(name="The second item")])
    )
    await maybe_async(item_repo.session.commit())
    await maybe_async(tag_repo.session.commit())
    assert len(new_items) > 0
    first_item_id = new_items[0].id
    new_items[1].id
    update_data = {
        "name": "A modified Name",
        "tag_names": ["A new tag"],
        "id": first_item_id,
    }
    tags_to_add = await maybe_async(tag_repo.list(CollectionFilter("name", update_data.pop("tag_names", []))))  # type: ignore
    assert len(tags_to_add) > 0
    assert tags_to_add[0].id is not None
    update_data["tags"] = tags_to_add  # type: ignore[assignment]
    updated_obj = await maybe_async(item_repo.update(item_model(**update_data), auto_refresh=False))
    await maybe_async(item_repo.session.commit())
    assert len(updated_obj.tags) > 0
    assert updated_obj.tags[0].name == "A new tag"


async def test_repo_health_check(author_repo: AuthorRepository) -> None:
    healthy = await maybe_async(author_repo.check_health(author_repo.session))
    assert healthy
