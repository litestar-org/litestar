"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Generator, Literal, Type, Union, cast
from uuid import uuid4

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_lazyfixture import lazy_fixture
from sqlalchemy import Engine, Table, insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
)
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
from tests.helpers import maybe_async
from tests.unit.test_contrib.test_sqlalchemy import models_bigint, models_uuid

from .helpers import update_raw_records

RepositoryPKType = Literal["uuid", "bigint"]
AuthorModel = Type[Union[models_uuid.UUIDAuthor, models_bigint.BigIntAuthor]]
RuleModel = Type[Union[models_uuid.UUIDRule, models_bigint.BigIntRule]]
ModelWithFetchedValue = Type[Union[models_uuid.UUIDModelWithFetchedValue, models_bigint.BigIntModelWithFetchedValue]]
ItemModel = Type[Union[models_uuid.UUIDItem, models_bigint.BigIntItem]]
TagModel = Type[Union[models_uuid.UUIDTag, models_bigint.BigIntTag]]

AuthorRepository = Union[
    models_uuid.AuthorAsyncRepository,
    models_uuid.AuthorSyncRepository,
    models_bigint.AuthorSyncRepository,
    models_bigint.AuthorSyncRepository,
]

RuleRepository = Union[
    models_uuid.RuleSyncRepository,
    models_uuid.RuleAsyncRepository,
    models_bigint.RuleSyncRepository,
    models_bigint.RuleAsyncRepository,
]

BookRepository = Union[
    models_uuid.BookSyncRepository,
    models_uuid.BookAsyncRepository,
    models_bigint.BookSyncRepository,
    models_bigint.BookAsyncRepository,
]

TagRepository = Union[
    models_uuid.TagSyncRepository,
    models_uuid.TagAsyncRepository,
    models_bigint.TagSyncRepository,
    models_bigint.TagAsyncRepository,
]

ItemRepository = Union[
    models_uuid.ItemSyncRepository,
    models_uuid.ItemAsyncRepository,
    models_bigint.ItemSyncRepository,
    models_bigint.ItemAsyncRepository,
]

ModelWithFetchedValueRepository = Union[
    models_uuid.ModelWithFetchedValueSyncRepository,
    models_uuid.ModelWithFetchedValueAsyncRepository,
    models_bigint.ModelWithFetchedValueSyncRepository,
    models_bigint.ModelWithFetchedValueAsyncRepository,
]


@pytest.fixture(params=["uuid", "bigint"])
def repository_pk_type(request: FixtureRequest) -> RepositoryPKType:
    return cast(RepositoryPKType, request.param)


@pytest.fixture()
def author_model(repository_pk_type: RepositoryPKType) -> AuthorModel:
    if repository_pk_type == "uuid":
        return models_uuid.UUIDAuthor
    return models_bigint.BigIntAuthor


@pytest.fixture()
def rule_model(repository_pk_type: RepositoryPKType) -> RuleModel:
    if repository_pk_type == "bigint":
        return models_bigint.BigIntRule
    return models_uuid.UUIDRule


@pytest.fixture()
def model_with_fetched_value(repository_pk_type: RepositoryPKType) -> ModelWithFetchedValue:
    if repository_pk_type == "bigint":
        return models_bigint.BigIntModelWithFetchedValue
    return models_uuid.UUIDModelWithFetchedValue


@pytest.fixture()
def item_model(repository_pk_type: RepositoryPKType) -> ItemModel:
    if repository_pk_type == "bigint":
        return models_bigint.BigIntItem
    return models_uuid.UUIDItem


@pytest.fixture()
def tag_model(repository_pk_type: RepositoryPKType) -> TagModel:
    if repository_pk_type == "uuid":
        return models_uuid.UUIDTag
    return models_bigint.BigIntTag


@pytest.fixture()
def book_model(repository_pk_type: RepositoryPKType) -> type[models_uuid.UUIDBook | models_bigint.BigIntBook]:
    if repository_pk_type == "uuid":
        return models_uuid.UUIDBook
    return models_bigint.BigIntBook


@pytest.fixture()
def new_pk_id(repository_pk_type: RepositoryPKType) -> Any:
    if repository_pk_type == "uuid":
        return uuid4()
    return 10


@pytest.fixture()
def existing_author_ids(raw_authors: list[dict[str, Any]]) -> Generator[Any, None, None]:
    return (author["id"] for author in raw_authors)


@pytest.fixture()
def first_author_id(raw_authors: list[dict[str, Any]]) -> Any:
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
    engine = cast(Engine, request.getfixturevalue(request.param))
    if engine.dialect.name.startswith("spanner") and repository_pk_type == "bigint":
        pytest.skip()
    return engine


@pytest.fixture()
def raw_authors(request: FixtureRequest, repository_pk_type: RepositoryPKType) -> list[dict[str, Any]]:
    if repository_pk_type == "bigint":
        authors = request.getfixturevalue("raw_authors_bigint")
    else:
        authors = request.getfixturevalue("raw_authors_uuid")
    return cast("list[dict[str, Any]]", authors)


@pytest.fixture()
def raw_rules(request: FixtureRequest, repository_pk_type: RepositoryPKType) -> list[dict[str, Any]]:
    if repository_pk_type == "bigint":
        rules = request.getfixturevalue("raw_rules_bigint")
    else:
        rules = request.getfixturevalue("raw_rules_uuid")
    return cast("list[dict[str, Any]]", rules)


def _seed_db_sync(
    *,
    engine: Engine,
    raw_authors: list[dict[str, Any]],
    raw_rules: list[dict[str, Any]],
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
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
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
    raw_authors: list[dict[str, Any]],
    raw_rules: list[dict[str, Any]],
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
    raw_authors: list[dict[str, Any]],
    raw_rules: list[dict[str, Any]],
    seed_db_sync: None,
) -> Generator[Session, None, None]:
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
    raw_authors: list[dict[str, Any]],
    raw_rules: list[dict[str, Any]],
    author_model: AuthorModel,
    rule_model: RuleModel,
) -> None:
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
    if isinstance(request.param, AsyncSession):
        request.getfixturevalue("seed_db_async")
    else:
        request.getfixturevalue("seed_db_sync")
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def repository_module(repository_pk_type: RepositoryPKType) -> Any:
    if repository_pk_type == "uuid":
        return models_uuid
    return models_bigint


@pytest.fixture()
def author_repo(any_session: AsyncSession | Session, repository_module: Any) -> AuthorRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.AuthorAsyncRepository(session=any_session)
    else:
        repo = repository_module.AuthorSyncRepository(session=any_session)
    return cast(AuthorRepository, repo)


@pytest.fixture()
def rule_repo(any_session: AsyncSession | Session, repository_module: Any) -> RuleRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.RuleAsyncRepository(session=any_session)
    else:
        repo = repository_module.RuleSyncRepository(session=any_session)
    return cast(RuleRepository, repo)


@pytest.fixture()
def book_repo(any_session: AsyncSession | Session, repository_module: Any) -> BookRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.BookAsyncRepository(session=any_session)
    else:
        repo = repository_module.BookSyncRepository(session=any_session)
    return cast(BookRepository, repo)


@pytest.fixture()
def tag_repo(any_session: AsyncSession | Session, repository_module: Any) -> ItemRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.TagAsyncRepository(session=any_session)
    else:
        repo = repository_module.TagSyncRepository(session=any_session)

    return cast(ItemRepository, repo)


@pytest.fixture()
def item_repo(any_session: AsyncSession | Session, repository_module: Any) -> ItemRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ItemAsyncRepository(session=any_session)
    else:
        repo = repository_module.ItemSyncRepository(session=any_session)

    return cast(ItemRepository, repo)


@pytest.fixture()
def model_with_fetched_value_repo(
    any_session: AsyncSession | Session, repository_module: Any
) -> ModelWithFetchedValueRepository:
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ModelWithFetchedValueAsyncRepository(session=any_session)
    else:
        repo = repository_module.ModelWithFetchedValueSyncRepository(session=any_session)
    return cast(ModelWithFetchedValueRepository, repo)


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


async def test_repo_count_method(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    assert await maybe_async(author_repo.count()) == 2


async def test_repo_list_and_count_method(raw_authors: list[dict[str, Any]], author_repo: AuthorRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors)
    collection, count = await maybe_async(author_repo.list_and_count())
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_list_and_count_method_empty(book_repo: BookRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    collection, count = await maybe_async(book_repo.list_and_count())
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


async def test_repo_created_updated(
    author_repo: AuthorRepository, book_model: type[models_uuid.UUIDBook | models_bigint.BigIntBook]
) -> None:
    """Test SQLALchemy created_at - updated_at.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    author = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    assert author.created_at is not None
    assert author.updated_at is not None
    original_update_dt = author.updated_at

    author.books.append(book_model(title="Testing"))
    author = await maybe_async(author_repo.update(author))
    assert author.updated_at > original_update_dt


async def test_repo_list_method(
    raw_authors_uuid: list[dict[str, Any]],
    author_repo: AuthorRepository,
) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection = await maybe_async(author_repo.list())
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_add_method(
    raw_authors: list[dict[str, Any]], author_repo: AuthorRepository, author_model: AuthorModel
) -> None:
    """Test SQLALchemy Add.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors) + 1
    new_author = author_model(name="Testing", dob=datetime.now().date())
    obj = await maybe_async(author_repo.add(new_author))
    count = await maybe_async(author_repo.count())
    assert exp_count == count
    assert isinstance(obj, author_model)
    assert new_author.name == obj.name
    assert obj.id is not None


async def test_repo_add_many_method(
    raw_authors: list[dict[str, Any]], author_repo: AuthorRepository, author_model: AuthorModel
) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    if author_repo._dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    objs = await maybe_async(author_repo.list())
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = await maybe_async(author_repo.update_many(objs))
    for obj in objs:
        assert obj.name.startswith("Update")


async def test_repo_exists_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exists = await maybe_async(author_repo.exists(id=first_author_id))
    assert exists


async def test_repo_update_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get(first_author_id))
    obj.name = "Updated Name"
    updated_obj = await maybe_async(author_repo.update(obj))
    assert updated_obj.name == obj.name


async def test_repo_delete_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.delete(first_author_id))
    assert obj.id == first_author_id


async def test_repo_delete_many_method(author_repo: AuthorRepository, author_model: AuthorModel) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get(first_author_id))
    assert obj.name == "Agatha Christie"


async def test_repo_get_one_or_none_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one_or_none(id=first_author_id))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await maybe_async(author_repo.get_one_or_none(name="I don't exist"))
    assert none_obj is None


async def test_repo_get_one_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one(id=first_author_id))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await author_repo.get_one(name="I don't exist")


async def test_repo_get_or_create_method(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj, existing_created = await maybe_async(author_repo.get_or_create(name="Agatha Christie"))
    assert existing_obj.id == first_author_id
    assert existing_created is False
    new_obj, new_created = await maybe_async(author_repo.get_or_create(name="New Author"))
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


async def test_repo_get_or_create_match_filter(author_repo: AuthorRepository, first_author_id: Any) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    author_repo: AuthorRepository, existing_author_ids: Generator[Any], author_model: AuthorModel
) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy before after filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy before after filter.
    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
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
    """Test SQLALchemy search filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

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
    """Test SQLALchemy not in search filter.
    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

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
    """Test SQLALchemy order by filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="desc")))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="asc")))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_collection(author_repo: AuthorRepository, existing_author_ids: Generator[Any]) -> None:
    """Test SQLALchemy collection filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    first_author_id = next(existing_author_ids)
    second_author_id = next(existing_author_ids)
    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[first_author_id])))
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[second_author_id])))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_not_in_collection(
    author_repo: AuthorRepository, existing_author_ids: Generator[Any]
) -> None:
    """Test SQLALchemy collection filter.
    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    first_author_id = next(existing_author_ids)
    second_author_id = next(existing_author_ids)
    existing_obj = await maybe_async(author_repo.list(NotInCollectionFilter(field_name="id", values=[first_author_id])))
    assert existing_obj[0].name == "Leo Tolstoy"

    existing_obj = await maybe_async(
        author_repo.list(NotInCollectionFilter(field_name="id", values=[second_author_id]))
    )
    assert existing_obj[0].name == "Agatha Christie"


async def test_repo_json_methods(
    raw_rules_uuid: list[dict[str, Any]], rule_repo: RuleRepository, rule_model: RuleModel
) -> None:
    """Test SQLALchemy JSON.

    Args:
        raw_rules_uuid (list[dict[str, Any]]): list of rules pre-seeded into the mock repository
        rules_repo (AuthorSyncRepository): The rules mock repository
    """
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
    """Test SQLALchemy fetched value in various places.

    Args:
        model_with_fetched_value_repo (ModelWithFetchedValueAsyncRepository): The author mock repository
    """

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
    """Test SQLALchemy fetched value in various places.

    Args:
        item_repo (ItemAsyncRepository): The item mock repository
        tag_repo (TagAsyncRepository): The tag mock repository
    """

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
    update_data["tags"] = tags_to_add
    updated_obj = await maybe_async(item_repo.update(item_model(**update_data), auto_refresh=False))
    await maybe_async(item_repo.session.commit())
    assert len(updated_obj.tags) > 0
    assert updated_obj.tags[0].name == "A new tag"


async def test_repo_health_check(author_repo: AuthorRepository) -> None:
    """Test SQLALchemy health check.

    Args:
        author_repo (AuthorAsyncRepository): The mock repository
    """

    healthy = await maybe_async(author_repo.check_health(author_repo.session))
    assert healthy
