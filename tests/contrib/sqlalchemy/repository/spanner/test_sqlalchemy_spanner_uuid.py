"""Unit tests for the SQLAlchemy Repository implementation for psycopg."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Generator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from tests.contrib.sqlalchemy.models_uuid import (
    AuthorSyncRepository,
    BookSyncRepository,
    RuleSyncRepository,
    UUIDAuthor,
    UUIDRule,
)
from tests.contrib.sqlalchemy.repository import sqlalchemy_sync_uuid_tests as st

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="docker not available on this platform"),
    pytest.mark.usefixtures("spanner_service"),
    pytest.mark.sqlalchemy_integration,
    pytest.mark.sqlalchemy_spanner,
]


@pytest.fixture(autouse=True)
def set_spanner_emulator_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPANNER_EMULATOR_HOST", "localhost:9010")


@pytest.fixture(autouse=True)
def set_google_cloud_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "emulator-test-project")


@pytest.fixture(name="engine")
def fx_engine(docker_ip: str) -> Engine:
    """Postgresql instance for end-to-end testing.

    Args:
        docker_ip: IP address for TCP connection to Docker containers.

    Returns:
        Async SQLAlchemy engine instance.
    """
    return create_engine(
        "spanner+spanner:///projects/emulator-test-project/instances/test-instance/databases/test-database",
        echo=True,
    )


@pytest.fixture(name="session")
def fx_session(
    engine: Engine,
    raw_authors_uuid: list[dict[str, Any]],
    raw_books_uuid: list[dict[str, Any]],
    raw_rules_uuid: list[dict[str, Any]],
) -> Generator[Session, None, None]:
    for raw_author in raw_authors_uuid:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created_at"] = datetime.strptime(raw_author["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
        raw_author["updated_at"] = datetime.strptime(raw_author["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(
            timezone.utc
        )
    for raw_rule in raw_rules_uuid:
        raw_rule["created_at"] = datetime.strptime(raw_rule["created_at"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
        raw_rule["updated_at"] = datetime.strptime(raw_rule["updated_at"], "%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc)
    with engine.begin() as txn:
        objs = []
        for tbl in UUIDAuthor.registry.metadata.sorted_tables:
            if tbl.description.startswith("uuid"):
                objs.append(tbl)
        UUIDAuthor.registry.metadata.create_all(txn, tables=objs)

    session = sessionmaker(bind=engine)()
    try:
        author_repo = AuthorSyncRepository(session=session)
        for author in raw_authors_uuid:
            _ = author_repo.get_or_create(match_fields="name", **author)
        if not bool(os.environ.get("SPANNER_EMULATOR_HOST")):
            rule_repo = RuleSyncRepository(session=session)
            for rule in raw_rules_uuid:
                _ = rule_repo.add(
                    UUIDRule(**rule),
                )
        yield session
    finally:
        session.rollback()
        session.close()
    with engine.begin() as txn:
        UUIDAuthor.registry.metadata.drop_all(txn, tables=objs)


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
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_filter_by_kwargs_with_incorrect_attribute_name(author_repo=author_repo)


def test_repo_count_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy count.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_count_method(author_repo=author_repo)


def test_repo_list_and_count_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_list_and_count_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


def test_repo_list_and_count_method_empty(book_repo: BookSyncRepository) -> None:
    """Test SQLALchemy list with count.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """

    st.test_repo_list_and_count_method_empty(book_repo=book_repo)


def test_repo_list_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_list_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


def test_repo_add_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy list.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_add_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


def test_repo_add_many_method(raw_authors_uuid: list[dict[str, Any]], author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Add Many.

    Args:
        raw_authors_uuid (list[dict[str, Any]]): list of authors pre-seeded into the mock repository
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_add_many_method(raw_authors_uuid=raw_authors_uuid, author_repo=author_repo)


# there's an emulator bug that causes this one to fail.
@pytest.mark.skipif(bool(os.environ.get("SPANNER_EMULATOR_HOST")), reason="Skipped on emulator")
@pytest.mark.xfail
def test_repo_update_many_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Update Many.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_update_many_method(author_repo=author_repo)


def test_repo_exists_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy exists.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_exists_method(author_repo=author_repo)


def test_repo_update_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Update.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_update_method(author_repo=author_repo)


def test_repo_delete_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_delete_method(author_repo=author_repo)


def test_repo_delete_many_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy delete many.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_delete_many_method(author_repo=author_repo)


def test_repo_get_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_get_method(author_repo=author_repo)


def test_repo_get_one_or_none_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_get_one_or_none_method(author_repo=author_repo)


def test_repo_get_one_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get One.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_get_one_method(author_repo=author_repo)


def test_repo_get_or_create_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get or create.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_get_or_create_method(author_repo=author_repo)


def test_repo_get_or_create_match_filter(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Get or create with a match filter

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_get_or_create_match_filter(author_repo=author_repo)


def test_repo_upsert_method(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy upsert.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_upsert_method(author_repo=author_repo)


def test_repo_filter_before_after(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy BeforeAfter filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_filter_before_after(author_repo=author_repo)


def test_repo_filter_search(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Search filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_filter_search(author_repo=author_repo)


def test_repo_filter_order_by(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Order By filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_filter_order_by(author_repo=author_repo)


def test_repo_filter_collection(author_repo: AuthorSyncRepository) -> None:
    """Test SQLALchemy Collection filter.

    Args:
        author_repo (AuthorRepository): The author mock repository
    """
    st.test_repo_filter_collection(author_repo=author_repo)


# there's an emulator bug that causes this one to fail.
# The current google tests disable JSON tests when using the emulator.
# https://github.com/googleapis/python-spanner-sqlalchemy/blob/main/test/test_suite_20.py#L2853
@pytest.mark.skipif(bool(os.environ.get("SPANNER_EMULATOR_HOST")), reason="Skipped on emulator")
@pytest.mark.xfail
def test_repo_json_methods(
    raw_rules_uuid: list[dict[str, Any]],
    rule_repo: RuleSyncRepository,
) -> None:
    """Test SQLALchemy Collection filter.

    Args:
        raw_rules_uuid (list[dict[str, Any]]): list of rules pre-seeded into the mock repository
        rule_repo (RuleSyncRepository): The rules mock repository
    """
    st.test_repo_json_methods(raw_rules_uuid=raw_rules_uuid, rule_repo=rule_repo)
