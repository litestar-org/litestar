"""Unit tests for the SQLAlchemy Repository implementation for psycopg."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Generator, cast
from uuid import UUID, uuid4

import pytest
from _pytest.fixtures import FixtureRequest
from sqlalchemy import Engine, Table, insert
from sqlalchemy.orm import Session, sessionmaker

from litestar.contrib.repository.exceptions import RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, OrderBy, SearchFilter
from litestar.contrib.sqlalchemy import base
from tests.contrib.sqlalchemy.models_uuid import (
    AuthorSyncRepository,
    BookSyncRepository,
    RuleSyncRepository,
    UUIDAuthor,
    UUIDRule,
)

pytestmark = [pytest.mark.sqlalchemy_integration]


@pytest.fixture(
    params=[
        pytest.param("duckdb_engine", marks=pytest.mark.sqlalchemy_duckdb),
        pytest.param("oracle_engine", marks=pytest.mark.sqlalchemy_oracledb),
        pytest.param("psycopg_engine", marks=pytest.mark.sqlalchemy_psycopg_sync),
        pytest.param("sqlite_engine", marks=pytest.mark.sqlalchemy_sqlite),
        pytest.param("spanner_engine", marks=pytest.mark.sqlalchemy_spanner),
    ]
)
def engine(request: FixtureRequest) -> Engine:
    return cast(Engine, request.getfixturevalue(request.param))


def _seed_db(
    engine: Engine,
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
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
    for raw_author in raw_rules_uuid:
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)

    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)

    with engine.begin() as conn:
        for author in raw_authors_uuid:
            conn.execute(insert(UUIDAuthor).values(author))
        for rule in raw_rules_uuid:
            conn.execute(insert(UUIDRule).values(rule))


def _seed_spanner(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_books_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> list[Table]:
    for raw_author in raw_authors_uuid:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
    for raw_rule in raw_rules_uuid:
        raw_rule["created"] = datetime.strptime(raw_rule["created"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
        raw_rule["updated"] = datetime.strptime(raw_rule["updated"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)

    with engine.begin() as txn:
        objs = []
        for tbl in UUIDAuthor.registry.metadata.sorted_tables:
            if tbl.description.startswith("uuid"):
                objs.append(tbl)
        UUIDAuthor.registry.metadata.create_all(txn, tables=objs)
    return objs


@pytest.fixture(autouse=True)
def seed_db(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_books_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> None:
    if engine.dialect.name.startswith("spanner"):
        _seed_spanner(engine, raw_authors_uuid, raw_books_uuid, raw_rules_uuid)
    else:
        _seed_db(engine, raw_authors_uuid, raw_books_uuid, raw_rules_uuid)


@pytest.fixture()
def session(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
    seed_db: None,
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
            UUIDAuthor.registry.metadata.drop_all(txn, tables=seed_db)
    else:
        try:
            yield session
        finally:
            session.rollback()
            session.close()


@pytest.fixture(name="author_repo")
def fx_author_repo(session: Session) -> AuthorSyncRepository:
    return AuthorSyncRepository(session=session)


@pytest.fixture(name="book_repo")
def fx_book_repo(session: Session) -> BookSyncRepository:
    return BookSyncRepository(session=session)


@pytest.fixture(name="rule_repo")
def fx_rule_repo(session: Session) -> RuleSyncRepository:
    return RuleSyncRepository(session=session)


def test_filter_by_kwargs_with_incorrect_attribute_name(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy filter by kwargs with invalid column name.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    with pytest.raises(RepositoryError):
        author_repo.filter_collection_by_kwargs(author_repo.statement, whoops="silly me")


def test_repo_count_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    assert author_repo.count() == 2


def test_repo_list_and_count_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorSyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection, count = author_repo.list_and_count()
    assert exp_count == count
    assert isinstance(collection, list)
    assert len(collection) == exp_count


def test_repo_list_and_count_method_empty(book_repo: BookSyncRepository) -> None:
    """Test SQLALchemy list with count in asyncpg.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorSyncRepository): The author mock repository
    """

    collection, count = book_repo.list_and_count()
    assert 0 == count
    assert isinstance(collection, list)
    assert len(collection) == 0


def test_repo_list_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorSyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid)
    collection = author_repo.list()
    assert isinstance(collection, list)
    assert len(collection) == exp_count


def test_repo_add_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Add.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorSyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid) + 1
    new_author = UUIDAuthor(name="Testing", dob=datetime.now().date())
    obj = author_repo.add(new_author)
    count = author_repo.count()
    assert exp_count == count
    assert isinstance(obj, UUIDAuthor)
    assert new_author.name == obj.name
    assert obj.id is not None


def test_repo_add_many_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorSyncRepository): The author mock repository
    """
    exp_count = len(raw_authors_uuid) + 2
    objs = author_repo.add_many(
        [UUIDAuthor(name="Testing 2", dob=datetime.now().date()), UUIDAuthor(name="Cody", dob=datetime.now().date())]
    )
    count = author_repo.count()
    assert exp_count == count
    assert isinstance(objs, list)
    assert len(objs) == 2
    for obj in objs:
        assert obj.id is not None
        assert obj.name in {"Testing 2", "Cody"}


def test_repo_update_many_method(author_repo: AuthorSyncRepository, engine: Engine) -> None:
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    if engine.dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    objs = author_repo.list()
    for idx, obj in enumerate(objs):
        obj.name = f"Update {idx}"
    objs = author_repo.update_many(objs)
    for obj in objs:
        assert obj.name.startswith("Update")


def test_repo_exists_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    exists = author_repo.exists(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert exists


def test_repo_update_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    obj = author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    obj.name = "Updated Name"
    updated_obj = author_repo.update(obj)
    assert updated_obj.name == obj.name


def test_repo_delete_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    obj = author_repo.delete(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")


def test_repo_delete_many_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    data_to_insert = []
    for chunk in range(0, 1000):
        data_to_insert.append(
            UUIDAuthor(
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
        author_repo (AuthorSyncRepository): The author mock repository
    """
    obj = author_repo.get(UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj.name == "Agatha Christie"


def test_repo_get_one_or_none_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    obj = author_repo.get_one_or_none(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    none_obj = author_repo.get_one_or_none(name="I don't exist")
    assert none_obj is None


def test_repo_get_one_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    obj = author_repo.get_one(id=UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"))
    assert obj is not None
    assert obj.name == "Agatha Christie"
    with pytest.raises(RepositoryError):
        _ = author_repo.get_one(name="I don't exist")


def test_repo_get_or_create_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
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
        author_repo (AuthorSyncRepository): The author mock repository
    """
    now = datetime.now()
    existing_obj, existing_created = author_repo.get_or_create(
        match_fields="name", name="Agatha Christie", dob=now.date()
    )
    assert existing_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert existing_obj.dob == now.date()
    assert existing_created is False


def test_repo_upsert_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    existing_obj = author_repo.get_one(name="Agatha Christie")
    existing_obj.name = "Agatha C."
    upsert_update_obj = author_repo.upsert(existing_obj)
    assert upsert_update_obj.id == UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")
    assert upsert_update_obj.name == "Agatha C."

    upsert_insert_obj = author_repo.upsert(UUIDAuthor(name="An Author"))
    assert upsert_insert_obj.id is not None
    assert upsert_insert_obj.name == "An Author"

    # ensures that it still works even if the ID is added before insert
    upsert2_insert_obj = author_repo.upsert(UUIDAuthor(id=uuid4(), name="Another Author"))
    assert upsert2_insert_obj.id is not None
    assert upsert2_insert_obj.name == "Another Author"


def test_repo_filter_before_after(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy before after filter.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """
    before_filter = BeforeAfter(
        field_name="created_at",
        before=datetime.strptime("2023-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        after=None,
    )
    existing_obj = author_repo.list(before_filter)
    assert existing_obj[0].name == "Leo Tolstoy"

    after_filter = BeforeAfter(
        field_name="created_at",
        after=datetime.strptime("2023-03-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc),
        before=None,
    )
    existing_obj = author_repo.list(after_filter)
    assert existing_obj[0].name == "Agatha Christie"


def test_repo_filter_search(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy search filter.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """

    existing_obj = author_repo.list(SearchFilter(field_name="name", value="gath", ignore_case=False))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=False))
    # sqlite & mysql are case insensitive by default with a `LIKE`
    dialect = author_repo.session.bind.dialect.name if author_repo.session.bind else "default"
    if dialect in {"sqlite", "mysql"}:
        expected_objs = 1
    else:
        expected_objs = 0
    assert len(existing_obj) == expected_objs
    existing_obj = author_repo.list(SearchFilter(field_name="name", value="GATH", ignore_case=True))
    assert existing_obj[0].name == "Agatha Christie"


def test_repo_filter_order_by(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy order by filter.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """

    existing_obj = author_repo.list(OrderBy(field_name="created_at", sort_order="desc"))
    assert existing_obj[0].name == "Agatha Christie"
    existing_obj = author_repo.list(OrderBy(field_name="created_at", sort_order="asc"))
    assert existing_obj[0].name == "Leo Tolstoy"


def test_repo_filter_collection(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy collection filter.

    Args:
        author_repo (AuthorSyncRepository): The author mock repository
    """

    existing_obj = author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b")])
    )
    assert existing_obj[0].name == "Agatha Christie"

    existing_obj = author_repo.list(
        CollectionFilter(field_name="id", values=[UUID("5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2")])
    )
    assert existing_obj[0].name == "Leo Tolstoy"


def test_repo_json_methods(raw_rules_uuid: list[dict[str, Any]], rule_repo: RuleSyncRepository, engine: Engine) -> None:
    """Test SQLALchemy JSON.

    Args:
        raw_rules_uuid (list[dict[str, Any]]): list of rules pre-seeded into the mock repository
        rules_repo (AuthorSyncRepository): The rules mock repository
    """

    if engine.dialect.name.startswith("spanner") and os.environ.get("SPANNER_EMULATOR_HOST"):
        pytest.skip("Skipped on emulator")

    exp_count = len(raw_rules_uuid) + 1
    new_rule = UUIDRule(name="Testing", config={"an": "object"})
    obj = rule_repo.add(new_rule)
    count = rule_repo.count()
    assert exp_count == count
    assert isinstance(obj, UUIDRule)
    assert new_rule.name == obj.name
    assert new_rule.config == obj.config
    assert obj.id is not None

    obj.config = {"the": "update"}
    updated = rule_repo.update(obj)
    assert obj.config == updated.config

    get_obj, get_created = rule_repo.get_or_create(
        match_fields=["name"], name="Secondary loading rule.", config={"another": "object"}
    )
    assert get_created is False
    assert get_obj.id is not None
    assert get_obj.config == {"another": "object"}

    new_obj, new_created = rule_repo.get_or_create(match_fields=["name"], name="New rule.", config={"new": "object"})
    assert new_created is True
    assert new_obj.id is not None
    assert new_obj.config == {"new": "object"}
