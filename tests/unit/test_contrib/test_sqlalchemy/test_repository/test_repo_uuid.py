"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Generator, cast
from uuid import UUID, uuid4

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
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, OrderBy, SearchFilter
from litestar.contrib.sqlalchemy import base
from tests.unit.test_contrib.test_sqlalchemy.models_bigint import ItemSyncRepository
from tests.unit.test_contrib.test_sqlalchemy.models_uuid import (
    AuthorAsyncRepository,
    AuthorSyncRepository,
    BookAsyncRepository,
    BookSyncRepository,
    ItemAsyncRepository,
    ModelWithFetchedValueAsyncRepository,
    ModelWithFetchedValueSyncRepository,
    RuleAsyncRepository,
    RuleSyncRepository,
    TagAsyncRepository,
    TagSyncRepository,
    UUIDAuthor,
    UUIDBook,
    UUIDItem,
    UUIDModelWithFetchedValue,
    UUIDRule,
    UUIDTag,
)

from .helpers import maybe_async, update_raw_records


@pytest.fixture(
    params=[
        pytest.param("sqlite_engine", marks=pytest.mark.sqlalchemy_sqlite),
        pytest.param("duckdb_engine", marks=[pytest.mark.sqlalchemy_duckdb, pytest.mark.sqlalchemy_integration]),
        pytest.param("oracle_engine", marks=[pytest.mark.sqlalchemy_oracledb, pytest.mark.sqlalchemy_integration]),
        pytest.param("psycopg_engine", marks=[pytest.mark.sqlalchemy_psycopg_sync, pytest.mark.sqlalchemy_integration]),
        pytest.param("spanner_engine", marks=[pytest.mark.sqlalchemy_spanner, pytest.mark.sqlalchemy_integration]),
    ]
)
def engine(request: FixtureRequest) -> Engine:
    return cast(Engine, request.getfixturevalue(request.param))


def _seed_db_sync(
    *,
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> None:
    update_raw_records(raw_authors=raw_authors_uuid, raw_rules=raw_rules_uuid)

    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)

    with engine.begin() as conn:
        for author in raw_authors_uuid:
            conn.execute(insert(UUIDAuthor).values(author))
        for rule in raw_rules_uuid:
            conn.execute(insert(UUIDRule).values(rule))


def _seed_spanner(
    *,
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> list[Table]:
    update_raw_records(raw_authors=raw_authors_uuid, raw_rules=raw_rules_uuid)

    with engine.begin() as txn:
        objs = [tbl for tbl in UUIDAuthor.registry.metadata.sorted_tables if tbl.description.startswith("uuid")]
        UUIDAuthor.registry.metadata.create_all(txn, tables=objs)
    return objs


@pytest.fixture()
def seed_db_sync(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> None:
    if engine.dialect.name.startswith("spanner"):
        _seed_spanner(engine=engine, raw_authors_uuid=raw_authors_uuid, raw_rules_uuid=raw_rules_uuid)
    else:
        _seed_db_sync(engine=engine, raw_authors_uuid=raw_authors_uuid, raw_rules_uuid=raw_rules_uuid)


@pytest.fixture()
def session(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
    seed_db_sync: None,
) -> Generator[Session, None, None]:
    session = sessionmaker(bind=engine)()

    if engine.dialect.name.startswith("spanner"):
        try:
            author_repo = AuthorSyncRepository(session=session)
            for author in raw_authors_uuid:
                _ = author_repo.get_or_create(match_fields="name", **author)
            if not bool(os.environ.get("SPANNER_EMULATOR_HOST")):
                rule_repo = RuleSyncRepository(session=session)
                for rule in raw_rules_uuid:
                    _ = rule_repo.add(UUIDRule(**rule))
            yield session
        finally:
            session.rollback()
            session.close()
        with engine.begin() as txn:
            UUIDAuthor.registry.metadata.drop_all(txn, tables=seed_db_sync)
    else:
        try:
            yield session
        finally:
            session.rollback()
            session.close()


@pytest.fixture()
async def seed_db_async(
    async_engine: AsyncEngine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_books_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> None:
    # convert date/time strings to dt objects.
    for raw_author in raw_authors_uuid:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created_at"] = datetime.strptime(raw_author["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
        raw_author["updated_at"] = datetime.strptime(raw_author["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
    for raw_author in raw_rules_uuid:
        raw_author["created_at"] = datetime.strptime(raw_author["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
        raw_author["updated_at"] = datetime.strptime(raw_author["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )

    async with async_engine.begin() as conn:
        await conn.run_sync(base.orm_registry.metadata.drop_all)
        await conn.run_sync(base.orm_registry.metadata.create_all)
        await conn.execute(insert(UUIDAuthor).values(raw_authors_uuid))
        await conn.execute(insert(UUIDRule).values(raw_rules_uuid))


@pytest.fixture(params=[lazy_fixture("session"), lazy_fixture("async_session")], ids=["sync", "async"])
def any_session(request: FixtureRequest) -> AsyncSession | Session:
    if isinstance(request.param, AsyncSession):
        request.getfixturevalue("seed_db_async")
    else:
        request.getfixturevalue("seed_db_sync")
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def author_repo(any_session: AsyncSession | Session) -> AuthorAsyncRepository | AuthorSyncRepository:
    if isinstance(any_session, AsyncSession):
        return AuthorAsyncRepository(session=any_session)
    return AuthorSyncRepository(session=any_session)


@pytest.fixture()
def rule_repo(any_session: AsyncSession | Session) -> RuleAsyncRepository | RuleSyncRepository:
    if isinstance(any_session, AsyncSession):
        return RuleAsyncRepository(session=any_session)
    return RuleSyncRepository(session=any_session)


@pytest.fixture()
def book_repo(any_session: AsyncSession | Session) -> BookAsyncRepository | BookSyncRepository:
    if isinstance(any_session, AsyncSession):
        return BookAsyncRepository(session=any_session)
    return BookSyncRepository(session=any_session)


@pytest.fixture()
def tag_repo(any_session: AsyncSession | Session) -> TagAsyncRepository | TagSyncRepository:
    if isinstance(any_session, AsyncSession):
        return TagAsyncRepository(session=any_session)
    return TagSyncRepository(session=any_session)


@pytest.fixture()
def item_repo(any_session: AsyncSession | Session) -> ItemAsyncRepository | ItemSyncRepository:
    if isinstance(any_session, AsyncSession):
        return ItemAsyncRepository(session=any_session)
    return ItemSyncRepository(session=any_session)


@pytest.fixture()
def model_with_fetched_value_repo(
    any_session: AsyncSession | Session,
) -> ModelWithFetchedValueAsyncRepository | ModelWithFetchedValueSyncRepository:
    if isinstance(any_session, AsyncSession):
        return ModelWithFetchedValueAsyncRepository(session=any_session)
    return ModelWithFetchedValueSyncRepository(session=any_session)


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


async def test_repo_count_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    assert await maybe_async(author_repo.count()) == 2


async def test_repo_list_and_count_method(
    raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorAsyncRepository
) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection, count = await maybe_async(author_repo.list_and_count())
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_list_and_count_method_empty(book_repo: BookAsyncRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    collection, count = await maybe_async(book_repo.list_and_count())
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


async def test_repo_created_updated(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy created_at - updated_at.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    author = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    assert author.created_at is not None
    assert author.updated_at is not None
    original_update_dt = author.updated_at

    author.books.append(UUIDBook(title="Testing"))
    author = await maybe_async(author_repo.update(author))
    assert author.updated_at == original_update_dt


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
    collection = await maybe_async(author_repo.list())
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
    new_author = UUIDAuthor(name="Testing", dob=datetime.now().date())
    obj = await maybe_async(author_repo.add(new_author))
    count = await maybe_async(author_repo.count())
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
    objs = await maybe_async(
        author_repo.add_many(
            [
                UUIDAuthor(name="Testing 2", dob=datetime.now().date()),
                UUIDAuthor(name="Cody", dob=datetime.now().date()),
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


async def test_repo_update_many_method(author_repo: AuthorAsyncRepository) -> None:
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


async def test_repo_exists_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exists = await maybe_async(author_repo.exists(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    assert exists


async def test_repo_update_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    obj.name = "Updated Name"
    updated_obj = await maybe_async(author_repo.update(obj))
    assert updated_obj.name == obj.name


async def test_repo_delete_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.delete(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    assert obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")


async def test_repo_delete_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    data_to_insert = [
        UUIDAuthor(
            name="author name %d" % chunk,
        )
        for chunk in range(1000)
    ]
    _ = await maybe_async(author_repo.add_many(data_to_insert))
    all_objs = await maybe_async(author_repo.list())
    ids_to_delete = [existing_obj.id for existing_obj in all_objs]
    objs = await maybe_async(author_repo.delete_many(ids_to_delete))
    await maybe_async(author_repo.session.commit())
    assert len(objs) > 0
    data, count = await maybe_async(author_repo.list_and_count())
    assert data == []
    assert count == 0


async def test_repo_get_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    assert obj.name == "Agatha Christie"


async def test_repo_get_one_or_none_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one_or_none(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await maybe_async(author_repo.get_one_or_none(name="I don't exist"))
    assert none_obj is None


async def test_repo_get_one_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await author_repo.get_one(name="I don't exist")


async def test_repo_get_or_create_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj, existing_created = await maybe_async(author_repo.get_or_create(name="Agatha Christie"))
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_created is False
    new_obj, new_created = await maybe_async(author_repo.get_or_create(name="New Author"))
    assert new_obj.id is not None
    assert new_obj.name == "New Author"
    assert new_created


async def test_repo_get_or_create_match_filter(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    now = datetime.now()
    existing_obj, existing_created = await maybe_async(
        author_repo.get_or_create(match_fields="name", name="Agatha Christie", dob=now.date())
    )
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_obj.dob == now.date()
    assert existing_created is False


async def test_repo_upsert_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj = await maybe_async(author_repo.get_one(name="Agatha Christie"))
    existing_obj.name = "Agatha C."
    upsert_update_obj = await maybe_async(author_repo.upsert(existing_obj))
    assert upsert_update_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = await maybe_async(author_repo.upsert(UUIDAuthor(name="An Author")))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = await maybe_async(author_repo.upsert(UUIDAuthor(id=uuid4(), name="Another Author")))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"


async def test_repo_filter_before_after(author_repo: AuthorAsyncRepository) -> None:
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


async def test_repo_filter_search(author_repo: AuthorAsyncRepository) -> None:
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


async def test_repo_filter_order_by(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy order by filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="desc")))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = await maybe_async(author_repo.list(OrderBy(field_name="created_at", sort_order="asc")))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_filter_collection(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy collection filter.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """

    existing_obj = await maybe_async(
        author_repo.list(CollectionFilter(field_name="id", values=[UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")]))
    )
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = await maybe_async(
        author_repo.list(CollectionFilter(field_name="id", values=[UUID("5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2")]))
    )
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_json_methods(raw_rules_uuid: list[dict[str, Any]], rule_repo: RuleAsyncRepository) -> None:
    """Test SQLALchemy JSON.

    Args:
        raw_rules_uuid (list[dict[str, Any]]): list of rules pre-seeded into the mock repository
        rules_repo (AuthorSyncRepository): The rules mock repository
    """
    if rule_repo._dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    exp_count = len(raw_rules_uuid) + 1
    new_rule = UUIDRule(name="Testing", config={"an": "object"})
    obj = await maybe_async(rule_repo.add(new_rule))
    count = await maybe_async(rule_repo.count())
    assert exp_count == count
    assert isinstance(obj, UUIDRule)
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


async def test_repo_fetched_value(model_with_fetched_value_repo: ModelWithFetchedValueAsyncRepository) -> None:
    """Test SQLALchemy fetched value in various places.

    Args:
        model_with_fetched_value_repo (ModelWithFetchedValueAsyncRepository): The author mock repository
    """

    obj = await maybe_async(model_with_fetched_value_repo.add(UUIDModelWithFetchedValue(val=1)))
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


async def test_lazy_load(item_repo: ItemAsyncRepository, tag_repo: TagAsyncRepository) -> None:
    """Test SQLALchemy fetched value in various places.

    Args:
        item_repo (ItemAsyncRepository): The item mock repository
        tag_repo (TagAsyncRepository): The tag mock repository
    """

    tag_obj = await maybe_async(tag_repo.add(UUIDTag(name="A new tag")))
    assert tag_obj
    new_items = await maybe_async(
        item_repo.add_many([UUIDItem(name="The first item"), UUIDItem(name="The second item")])
    )
    assert len(new_items) > 0
    first_item_id = new_items[0].id
    new_items[1].id
    update_data = {"name": "A modified Name", "tag_names": ["A new tag"]}
    update_data.update({"id": first_item_id})  # type: ignore
    tags_to_add = await maybe_async(tag_repo.list(CollectionFilter("name", update_data.pop("tag_names", []))))
    assert len(tags_to_add) > 0
    update_data.update({"tags": tags_to_add})  # type: ignore
    updated_obj = await maybe_async(item_repo.update(UUIDItem(**update_data)))
    assert len(updated_obj.tags) > 0
