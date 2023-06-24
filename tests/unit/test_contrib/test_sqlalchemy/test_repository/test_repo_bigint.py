"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_lazyfixture import lazy_fixture
from sqlalchemy import Engine, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, OrderBy, SearchFilter
from litestar.contrib.sqlalchemy import base
from tests.unit.test_contrib.test_sqlalchemy.models_bigint import (
    AuthorAsyncRepository,
    AuthorSyncRepository,
    BigIntAuthor,
    BigIntBook,
    BigIntRule,
    BookAsyncRepository,
    BookSyncRepository,
    RuleAsyncRepository,
    RuleSyncRepository,
)

from .helpers import maybe_async, update_raw_records


@pytest.fixture()
async def seed_db_async(
    raw_authors_bigint: list[dict[str, Any]], raw_rules_bigint: list[dict[str, Any]], async_engine: AsyncEngine
) -> None:
    update_raw_records(raw_authors=raw_authors_bigint, raw_rules=raw_rules_bigint)

    async with async_engine.begin() as conn:
        await conn.run_sync(base.orm_registry.metadata.drop_all)
        await conn.run_sync(base.orm_registry.metadata.create_all)
        await conn.execute(insert(BigIntAuthor).values(raw_authors_bigint))
        await conn.execute(insert(BigIntRule).values(raw_rules_bigint))


@pytest.fixture()
def seed_db_sync(
    engine: Engine,
    raw_authors_bigint: list[dict[str, Any]],
    raw_rules_bigint: list[dict[str, Any]],
) -> None:
    update_raw_records(raw_authors=raw_authors_bigint, raw_rules=raw_rules_bigint)

    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)
        for author in raw_authors_bigint:
            conn.execute(insert(BigIntAuthor).values(author))
        for rule in raw_rules_bigint:
            conn.execute(insert(BigIntRule).values(rule))


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
    raw_authors_bigint: list[dict[str, Any]], author_repo: AuthorAsyncRepository
) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_bigint (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_bigint)
    collection, count = await maybe_async(author_repo.list_and_count())
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_list_and_count_method_empty(book_repo: BookAsyncRepository) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_bigint (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
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

    author.books.append(BigIntBook(title="Testing"))
    author = await maybe_async(author_repo.update(author))
    assert author.updated_at == original_update_dt


async def test_repo_list_method(raw_authors_bigint: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_bigint (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_bigint)
    collection = await maybe_async(author_repo.list())
    assert isinstance(collection, list)
    assert len(collection) == exp_count


async def test_repo_add_method(raw_authors_bigint: list[dict[str, Any]], author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Add.

    Args:
        raw_authors_bigint (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_bigint) + 1
    new_author = BigIntAuthor(name="Testing", dob=datetime.now())
    obj = await maybe_async(author_repo.add(new_author))
    count = await maybe_async(author_repo.count())
    assert exp_count == count
    assert isinstance(obj, BigIntAuthor)
    assert new_author.name == obj.name
    assert obj.id is not None


async def test_repo_add_many_method(
    raw_authors_bigint: list[dict[str, Any]], author_repo: AuthorAsyncRepository
) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_bigint (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_bigint) + 2
    objs = await maybe_async(
        author_repo.add_many(
            [BigIntAuthor(name="Testing 2", dob=datetime.now()), BigIntAuthor(name="Cody", dob=datetime.now())]
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
    exists = await maybe_async(author_repo.exists(id=2023))
    assert exists


async def test_repo_update_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get(2023))
    obj.name = "Updated Name"
    updated_obj = await maybe_async(author_repo.update(obj))
    assert updated_obj.name == obj.name


async def test_repo_delete_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.delete(2023))
    assert obj.id == 2023


async def test_repo_delete_many_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    data_to_insert = []
    for chunk in range(0, 1000):
        data_to_insert.append(
            BigIntAuthor(
                name="author name %d" % chunk,
            )
        )
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
    obj = await maybe_async(author_repo.get(2023))
    assert obj.name == "Agatha Christie"


async def test_repo_get_one_or_none_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one_or_none(id=2023))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = await maybe_async(author_repo.get_one_or_none(name="I don't exist"))
    assert none_obj is None


async def test_repo_get_one_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    obj = await maybe_async(author_repo.get_one(id=2023))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = await maybe_async(author_repo.get_one(name="I don't exist"))


async def test_repo_get_or_create_method(author_repo: AuthorAsyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorAsyncRepository): The author mock repository
    """
    existing_obj, existing_created = await maybe_async(author_repo.get_or_create(name="Agatha Christie"))
    assert existing_obj.id == 2023
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
    assert existing_obj.id == 2023
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
    assert upsert_update_obj.id == 2023
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = await maybe_async(author_repo.upsert(BigIntAuthor(name="An Author")))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = await maybe_async(author_repo.upsert(BigIntAuthor(id=10, name="Another Author")))
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
    if dialect in {"sqlite", "mysql"}:
        expected_objs = 1
    else:
        expected_objs = 0
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

    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[2023])))
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = await maybe_async(author_repo.list(CollectionFilter(field_name="id", values=[2024])))
    assert existing_obj[0].name == "Leo Tolstoy"


async def test_repo_json_methods(
    raw_rules_bigint: list[dict[str, Any]],
    rule_repo: RuleAsyncRepository,
) -> None:
    """Test SQLALchemy JSON.

    Args:
        raw_rules_bigint (list[dict[str, Any]]): list of rules pre-seeded into the mock repository
        rule_repo (AuthorAsyncRepository): The rules mock repository
    """
    exp_count = len(raw_rules_bigint) + 1
    new_rule = BigIntRule(name="Testing", config={"an": "object"})
    obj = await maybe_async(rule_repo.add(new_rule))
    count = await maybe_async(rule_repo.count())
    assert exp_count == count
    assert isinstance(obj, BigIntRule)
    assert new_rule.name == obj.name
    assert new_rule.config == obj.config
    assert obj.id is not None
    obj.config = {"the": "update"}
    updated = await maybe_async(rule_repo.update(obj))
    assert obj.config == updated.config

    get_obj, get_created = await maybe_async(
        rule_repo.get_or_create(
            match_fields=["name"],
            name="Secondary loading rule.",
            config={"another": "object"},
        )
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
