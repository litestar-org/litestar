"""Unit tests for the SQLAlchemy Repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Union, cast
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_lazyfixture import lazy_fixture
from pytest_mock import MockerFixture
from sqlalchemy import String
from sqlalchemy.exc import IntegrityError, InvalidRequestError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Mapped, Session, mapped_column

from litestar.contrib.repository.exceptions import ConflictError, RepositoryError
from litestar.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    LimitOffset,
    NotInCollectionFilter,
    OnBeforeAfter,
)
from litestar.contrib.sqlalchemy import base
from litestar.contrib.sqlalchemy.repository import (
    SQLAlchemyAsyncRepository,
    SQLAlchemySyncRepository,
    wrap_sqlalchemy_exception,
)
from tests.helpers import maybe_async

if TYPE_CHECKING:
    from pytest import MonkeyPatch


AnyMock = Union[MagicMock, AsyncMock]


@pytest.fixture()
def async_mock_repo() -> SQLAlchemyAsyncRepository:
    """SQLAlchemy repository with a mock model type."""

    class Repo(SQLAlchemyAsyncRepository[MagicMock]):
        """Repo with mocked out stuff."""

        model_type = MagicMock()  # pyright:ignore[reportGeneralTypeIssues]

    return Repo(session=AsyncMock(spec=AsyncSession, bind=MagicMock()), statement=MagicMock())


@pytest.fixture()
def sync_mock_repo() -> SQLAlchemySyncRepository:
    """SQLAlchemy repository with a mock model type."""

    class Repo(SQLAlchemySyncRepository[MagicMock]):
        """Repo with mocked out stuff."""

        model_type = MagicMock()  # pyright:ignore[reportGeneralTypeIssues]

    return Repo(session=MagicMock(spec=Session, bind=MagicMock()), statement=MagicMock())


@pytest.fixture(params=[lazy_fixture("sync_mock_repo"), lazy_fixture("async_mock_repo")])
def mock_repo(request: FixtureRequest) -> SQLAlchemyAsyncRepository:
    return cast(SQLAlchemyAsyncRepository, request.param)


@pytest.fixture()
def mock_session_scalars(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo.session, "scalars")


@pytest.fixture()
def mock_session_execute(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo.session, "scalars")


@pytest.fixture()
def mock_repo_list(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo, "list")


@pytest.fixture()
def mock_repo_execute(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo, "_execute")


@pytest.fixture()
def mock_repo_attach_to_session(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo, "_attach_to_session")


@pytest.fixture()
def mock_repo_count(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> AnyMock:
    return mocker.patch.object(mock_repo, "count")


def test_sqlalchemy_tablename() -> None:
    """Test the snake case conversion for table names."""

    class BigModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class TESTModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntAuditBase):
        """Inheriting from BigIntAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    assert BigModel.__tablename__ == "big_model"
    assert TESTModel.__tablename__ == "test_model"
    assert BigIntModel.__tablename__ == "big_int_model"


def test_sqlalchemy_sentinel(monkeypatch: MonkeyPatch) -> None:
    """Test the sqlalchemy sentinel column only exists on `UUIDPrimaryKey` models."""

    class AnotherModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        the_extra_col: Mapped[str] = mapped_column(String(length=100), nullable=True)  # pyright: ignore

    class TheTestModel(base.UUIDBase):
        """Inheriting from DeclarativeBase gives the model 'id'  columns."""

        the_extra_col: Mapped[str] = mapped_column(String(length=100), nullable=True)  # pyright: ignore

    class TheBigIntModel(base.BigIntBase):
        """Inheriting from DeclarativeBase gives the model 'id'  columns."""

        the_extra_col: Mapped[str] = mapped_column(String(length=100), nullable=True)  # pyright: ignore

    unloaded_cols = {"the_extra_col"}
    sa_instance_mock = MagicMock(unloaded=unloaded_cols)

    assert isinstance(AnotherModel._sentinel, InstrumentedAttribute)  # pyright: ignore
    assert isinstance(TheTestModel._sentinel, InstrumentedAttribute)  # pyright: ignore
    assert not hasattr(TheBigIntModel, "_sentinel")

    model1, model2, model3 = AnotherModel(), TheTestModel(), TheBigIntModel()
    monkeypatch.setattr(model1, "_sa_instance_state", sa_instance_mock)
    monkeypatch.setattr(model2, "_sa_instance_state", sa_instance_mock)
    monkeypatch.setattr(model3, "_sa_instance_state", sa_instance_mock)

    assert "created_at" not in model1.to_dict(exclude={"created_at"}).keys()
    assert "the_extra_col" not in model1.to_dict(exclude={"created_at"}).keys()
    assert "sa_orm_sentinel" not in model1.to_dict().keys()
    assert "sa_orm_sentinel" not in model2.to_dict().keys()
    assert "sa_orm_sentinel" not in model3.to_dict().keys()
    assert "_sentinel" not in model1.to_dict().keys()
    assert "_sentinel" not in model2.to_dict().keys()
    assert "_sentinel" not in model3.to_dict().keys()
    assert "the_extra_col" not in model1.to_dict().keys()


def test_wrap_sqlalchemy_integrity_error() -> None:
    """Test to ensure we wrap IntegrityError."""
    with pytest.raises(ConflictError), wrap_sqlalchemy_exception():
        raise IntegrityError(None, None, Exception())


def test_wrap_sqlalchemy_generic_error() -> None:
    """Test to ensure we wrap generic SQLAlchemy exceptions."""
    with pytest.raises(RepositoryError), wrap_sqlalchemy_exception():
        raise SQLAlchemyError


async def test_sqlalchemy_repo_add(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Test expected method calls for add operation."""
    mock_instance = MagicMock()

    instance = await maybe_async(mock_repo.add(mock_instance))

    assert instance is mock_instance
    mock_repo.session.add.assert_called_once_with(mock_instance)
    mock_repo.session.flush.assert_called_once()
    mock_repo.session.refresh.assert_called_once_with(mock_instance, attribute_names=None, with_for_update=None)
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_add_many(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    """Test expected method calls for add many operation."""

    class UUIDModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntAuditBase):
        """Inheriting from BigIntAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_instances = [MagicMock(), MagicMock(), MagicMock()]
    monkeypatch.setattr(mock_repo, "model_type", UUIDModel)
    mocker.patch.object(mock_repo.session, "scalars", return_value=mock_instances)

    instances = await maybe_async(mock_repo.add_many(mock_instances))

    assert len(instances) == 3
    for row in instances:
        assert row.id is not None
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_update_many(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    """Test expected method calls for update many operation."""

    class UUIDModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    class BigIntModel(base.BigIntAuditBase):
        """Inheriting from BigIntAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_instances = [MagicMock(), MagicMock(), MagicMock()]
    monkeypatch.setattr(mock_repo, "model_type", UUIDModel)
    mocker.patch.object(mock_repo.session, "scalars", return_value=mock_instances)

    instances = await maybe_async(mock_repo.update_many(mock_instances))

    assert len(instances) == 3
    for row in instances:
        assert row.id is not None

    mock_repo.session.flush.assert_called_once()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_delete(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> None:
    """Test expected method calls for delete operation."""
    mock_instance = MagicMock()
    mocker.patch.object(mock_repo, "get", return_value=mock_instance)
    instance = await maybe_async(mock_repo.delete("instance-id"))

    assert instance is mock_instance

    mock_repo.session.delete.assert_called_once_with(mock_instance)
    mock_repo.session.flush.assert_called_once()
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_delete_many_uuid(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_session_scalars: AnyMock,
    mock_session_execute: AnyMock,
    mock_repo_list: AnyMock,
) -> None:
    """Test expected method calls for delete operation."""

    class UUIDModel(base.UUIDAuditBase):
        """Inheriting from UUIDAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_instances = [MagicMock(), MagicMock(id=uuid4())]
    mock_session_scalars.return_value = mock_instances
    mock_session_execute.return_value = mock_instances
    mock_repo_list.return_value = mock_instances
    monkeypatch.setattr(mock_repo, "model_type", UUIDModel)
    monkeypatch.setattr(mock_repo.session.bind.dialect, "insertmanyvalues_max_parameters", 2)

    added_instances = await maybe_async(mock_repo.add_many(mock_instances))
    instances = await maybe_async(mock_repo.delete_many([obj.id for obj in added_instances]))

    assert len(instances) == len(mock_instances)
    mock_repo.session.flush.assert_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_delete_many_bigint(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_session_scalars: AnyMock,
    mock_session_execute: AnyMock,
    mock_repo_list: AnyMock,
) -> None:
    """Test expected method calls for delete operation."""

    class BigIntModel(base.BigIntAuditBase):
        """Inheriting from BigIntAuditBase gives the model 'created_at' and 'updated_at'
        columns."""

        ...

    mock_instances = [MagicMock(), MagicMock(id=uuid4())]
    mock_session_scalars.return_value = mock_instances
    mock_session_execute.return_value = mock_instances
    mock_repo_list.return_value = mock_instances
    monkeypatch.setattr(mock_repo, "model_type", BigIntModel)
    monkeypatch.setattr(mock_repo.session.bind.dialect, "insertmanyvalues_max_parameters", 2)

    added_instances = await maybe_async(mock_repo.add_many(mock_instances))
    instances = await maybe_async(mock_repo.delete_many([obj.id for obj in added_instances]))

    assert len(instances) == len(mock_instances)
    mock_repo.session.flush.assert_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_get_member(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock, mocker: MockerFixture
) -> None:
    """Test expected method calls for member get operation."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))

    instance = await maybe_async(mock_repo.get("instance-id"))

    assert instance is mock_instance
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_get_one_member(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for member get one operation."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))

    instance = await maybe_async(mock_repo.get_one(id="instance-id"))

    assert instance is mock_instance
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_get_or_create_member_existing(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_repo_execute: AnyMock,
    mock_repo_attach_to_session: AnyMock,
) -> None:
    """Test expected method calls for member get or create operation (existing)."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))
    mock_repo_attach_to_session.return_value = mock_instance

    instance, created = await maybe_async(mock_repo.get_or_create(id="instance-id", upsert=False))

    assert instance is mock_instance
    assert created is False
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.merge.assert_not_called()
    mock_repo.session.refresh.assert_not_called()


async def test_sqlalchemy_repo_get_or_create_member_existing_upsert(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_repo_execute: AnyMock,
    mock_repo_attach_to_session: AnyMock,
) -> None:
    """Test expected method calls for member get or create operation (existing)."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))
    mock_repo_attach_to_session.return_value = mock_instance

    instance, created = await maybe_async(
        mock_repo.get_or_create(id="instance-id", upsert=True, an_extra_attribute="yep")
    )

    assert instance is mock_instance
    assert created is False
    mock_repo.session.expunge.assert_not_called()
    mock_repo._attach_to_session.assert_called_once()
    mock_repo.session.flush.assert_called_once()
    mock_repo.session.refresh.assert_called_once_with(mock_instance, attribute_names=None, with_for_update=None)


async def test_sqlalchemy_repo_get_or_create_member_existing_no_upsert(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for member get or create operation (existing)."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))

    instance, created = await maybe_async(
        mock_repo.get_or_create(id="instance-id", upsert=False, an_extra_attribute="yep")
    )

    assert instance is mock_instance
    assert created is False
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.add.assert_not_called()
    mock_repo.session.refresh.assert_not_called()


async def test_sqlalchemy_repo_get_or_create_member_created(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for member get or create operation (created)."""
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    instance, created = await maybe_async(mock_repo.get_or_create(id="new-id"))

    assert instance is not None
    assert created is True
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.add.assert_called_once_with(instance)
    mock_repo.session.refresh.assert_called_once_with(instance, attribute_names=None, with_for_update=None)


async def test_sqlalchemy_repo_get_one_or_none_member(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for member get one or none operation (found)."""
    mock_instance = MagicMock()
    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_instance))

    instance = await maybe_async(mock_repo.get_one_or_none(id="instance-id"))

    assert instance is mock_instance
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_get_one_or_none_not_found(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for member get one or none operation (Not found)."""

    mock_repo_execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    instance = await maybe_async(mock_repo.get_one_or_none(id="instance-id"))

    assert instance is None
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_list(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test expected method calls for list operation."""
    mock_instances = [MagicMock(), MagicMock()]
    mock_repo_execute.return_value = MagicMock(scalars=MagicMock(return_value=mock_instances))

    instances = await maybe_async(mock_repo.list())

    assert instances == mock_instances
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_list_and_count(mock_repo: SQLAlchemyAsyncRepository, mocker: MockerFixture) -> None:
    """Test expected method calls for list operation."""
    mock_instances = [MagicMock(), MagicMock()]
    mock_count = len(mock_instances)
    mocker.patch.object(mock_repo, "_list_and_count_window", return_value=(mock_instances, mock_count))
    mocker.patch.object(mock_repo, "_list_and_count_window", return_value=(mock_instances, mock_count))

    instances, instance_count = await maybe_async(mock_repo.list_and_count())

    assert instances == mock_instances
    assert instance_count == mock_count
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_exists(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_repo_execute: AnyMock,
    mock_repo_count: AnyMock,
) -> None:
    """Test expected method calls for exists operation."""
    mock_repo_count.return_value = 1

    exists = await maybe_async(mock_repo.exists(id="my-id"))

    assert exists
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_count(
    mock_repo: SQLAlchemyAsyncRepository,
    monkeypatch: MonkeyPatch,
    mock_repo_execute: AnyMock,
    mock_repo_count: AnyMock,
) -> None:
    """Test expected method calls for list operation."""
    mock_repo_count.return_value = 1

    count = await maybe_async(mock_repo.count())

    assert count == 1
    mock_repo.session.commit.assert_not_called()


async def test_sqlalchemy_repo_list_with_pagination(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test list operation with pagination."""
    mock_repo_execute.return_value = MagicMock()
    mock_repo.statement.limit.return_value = mock_repo.statement
    mock_repo.statement.offset.return_value = mock_repo.statement

    await maybe_async(mock_repo.list(LimitOffset(2, 3)))

    mock_repo.statement.limit.assert_called_once_with(2)
    mock_repo.statement.limit().offset.assert_called_once_with(3)  # type:ignore[call-arg]


async def test_sqlalchemy_repo_list_with_before_after_filter(
    mock_repo: SQLAlchemyAsyncRepository, mock_repo_execute: AnyMock, mocker: MockerFixture
) -> None:
    """Test list operation with BeforeAfter filter."""
    mocker.patch.object(mock_repo.model_type.updated_at, "__lt__", return_value="lt")
    mocker.patch.object(mock_repo.model_type.updated_at, "__gt__", return_value="gt")

    mock_repo_execute.return_value = MagicMock()
    mock_repo.statement.where.return_value = mock_repo.statement

    await maybe_async(mock_repo.list(BeforeAfter("updated_at", datetime.max, datetime.min)))

    assert mock_repo.statement.where.call_count == 2
    mock_repo.statement.where.assert_has_calls([call("gt"), call("lt")], any_order=True)


async def test_sqlalchemy_repo_list_with_on_before_after_filter(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock, mocker: MockerFixture
) -> None:
    """Test list operation with BeforeAfter filter."""
    mocker.patch.object(mock_repo.model_type.updated_at, "__le__", return_value="le")
    mocker.patch.object(mock_repo.model_type.updated_at, "__ge__", return_value="ge")

    mock_repo_execute.return_value = MagicMock()
    mock_repo.statement.where.return_value = mock_repo.statement
    await maybe_async(mock_repo.list(OnBeforeAfter("updated_at", datetime.max, datetime.min)))

    assert mock_repo.statement.where.call_count == 2
    mock_repo.statement.where.assert_has_calls([call("ge"), call("le")], any_order=True)


async def test_sqlalchemy_repo_list_with_collection_filter(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test behavior of list operation given CollectionFilter."""
    field_name = "id"
    mock_repo_execute.return_value = MagicMock()
    mock_repo.statement.where.return_value = mock_repo.statement
    values = [1, 2, 3]

    await maybe_async(mock_repo.list(CollectionFilter(field_name, values)))

    mock_repo.statement.where.assert_called_once()
    getattr(mock_repo.model_type, field_name).in_.assert_called_once_with(values)


async def test_sqlalchemy_repo_list_with_not_in_collection_filter(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mock_repo_execute: AnyMock
) -> None:
    """Test behavior of list operation given CollectionFilter."""
    field_name = "id"
    mock_repo_execute.return_value = MagicMock()
    mock_repo.statement.where.return_value = mock_repo.statement
    values = [1, 2, 3]

    await maybe_async(mock_repo.list(NotInCollectionFilter(field_name, values)))

    mock_repo.statement.where.assert_called_once()
    getattr(mock_repo.model_type, field_name).notin_.assert_called_once_with(values)


async def test_sqlalchemy_repo_unknown_filter_type_raises(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Test that repo raises exception if list receives unknown filter type."""
    with pytest.raises(RepositoryError):
        await maybe_async(mock_repo.list("not a filter"))  # type:ignore[arg-type]


async def test_sqlalchemy_repo_update(
    mock_repo: SQLAlchemyAsyncRepository, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    """Test the sequence of repo calls for update operation."""
    id_ = 3
    mock_instance = MagicMock()
    mocker.patch.object(mock_repo, "get_id_attribute_value", return_value=id_)
    mocker.patch.object(mock_repo, "get")
    mock_repo.session.merge.return_value = mock_instance

    instance = await maybe_async(mock_repo.update(mock_instance))

    assert instance is mock_instance
    mock_repo.session.merge.assert_called_once_with(mock_instance)
    mock_repo.session.flush.assert_called_once()
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()
    mock_repo.session.refresh.assert_called_once_with(mock_instance, attribute_names=None, with_for_update=None)


async def test_sqlalchemy_repo_upsert(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Test the sequence of repo calls for upsert operation."""
    mock_instance = MagicMock()
    mock_repo.session.merge.return_value = mock_instance

    instance = await maybe_async(mock_repo.upsert(mock_instance))

    assert instance is mock_instance
    mock_repo.session.merge.assert_called_once_with(mock_instance)
    mock_repo.session.flush.assert_called_once()
    mock_repo.session.expunge.assert_not_called()
    mock_repo.session.commit.assert_not_called()
    mock_repo.session.refresh.assert_called_once_with(mock_instance, attribute_names=None, with_for_update=None)


async def test_attach_to_session_unexpected_strategy_raises_valueerror(
    mock_repo: SQLAlchemyAsyncRepository,
) -> None:
    """Test to hit the error condition in SQLAlchemy._attach_to_session()."""
    with pytest.raises(ValueError):
        await maybe_async(mock_repo._attach_to_session(MagicMock(), strategy="t-rex"))  # type:ignore[arg-type]


async def test_execute(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Simple test of the abstraction over `AsyncSession.execute()`"""
    _ = await maybe_async(mock_repo._execute(mock_repo.statement))
    mock_repo.session.execute.assert_called_once_with(mock_repo.statement)


def test_filter_in_collection_noop_if_collection_empty(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Ensures we don't filter on an empty collection."""
    mock_repo._filter_in_collection("id", [], statement=mock_repo.statement)
    mock_repo.statement.where.assert_not_called()  # type: ignore


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (datetime.max, datetime.min),
        (None, datetime.min),
        (datetime.max, None),
    ],
)
def test_filter_on_datetime_field(before: datetime, after: datetime, mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Test through branches of _filter_on_datetime_field()"""
    field_mock = MagicMock()
    field_mock.__gt__ = field_mock.__lt__ = lambda self, other: True

    mock_repo.model_type.updated_at = field_mock
    mock_repo._filter_on_datetime_field("updated_at", before=before, after=after, statement=mock_repo.statement)


def test_filter_collection_by_kwargs(mock_repo: SQLAlchemyAsyncRepository) -> None:
    """Test `filter_by()` called with kwargs."""
    _ = mock_repo.filter_collection_by_kwargs(mock_repo.statement, a=1, b=2)
    mock_repo.statement.filter_by.assert_called_once_with(a=1, b=2)


def test_filter_collection_by_kwargs_raises_repository_exception_for_attribute_error(
    mock_repo: SQLAlchemyAsyncRepository,
) -> None:
    """Test that we raise a repository exception if an attribute name is
    incorrect."""
    mock_repo.statement.filter_by = MagicMock(  # type:ignore[method-assign]
        side_effect=InvalidRequestError,
    )
    with pytest.raises(RepositoryError):
        _ = mock_repo.filter_collection_by_kwargs(mock_repo.statement, a=1)
