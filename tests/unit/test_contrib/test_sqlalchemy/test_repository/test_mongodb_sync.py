from datetime import datetime
from typing import Any, List
from unittest.mock import MagicMock, Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pymongo import UpdateOne
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from litestar.contrib.mongodb_motor.repository._sync import MongoDbSyncRepository
from litestar.contrib.mongodb_motor.repository._util import wrap_pymongo_exception
from litestar.contrib.repository import ConflictError, NotFoundError, RepositoryError
from litestar.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    FilterTypes,
    LimitOffset,
    OrderBy,
    SearchFilter,
)


class MockCursor:
    def __init__(self, return_value: Any):
        self.return_value = return_value

    def __iter__(self) -> Any:
        yield from self.return_value


@pytest.fixture()
def mock_repo() -> MongoDbSyncRepository:
    """Motor/PyMongo repository with a mock collection."""

    return MongoDbSyncRepository(collection=Mock(spec=Collection))


def test_wrap_pymongo_duplicate_key_error() -> None:
    """Test to ensure we wrap DuplicateKeyError."""
    with pytest.raises(ConflictError), wrap_pymongo_exception():
        raise DuplicateKeyError("")


def test_wrap_pymongo_generic_error() -> None:
    """Test to ensure we wrap generic PyMongoError exceptions."""
    with pytest.raises(RepositoryError), wrap_pymongo_exception():
        raise PyMongoError


def test_motor_repo_add(mock_repo: MongoDbSyncRepository) -> None:
    """Test expected method calls for add operation."""
    mock_instance = MagicMock()
    instance = mock_repo.add(mock_instance)
    assert instance is mock_instance
    mock_repo.collection.insert_one.assert_called_once_with(mock_instance)


def test_motor_repo_add_many(mock_repo: MongoDbSyncRepository) -> None:
    """Test expected method calls for add many operation."""
    instances_to_add = [{"foo": "bar"}, {"foo": "baz"}]
    instances = mock_repo.add_many(instances_to_add)
    assert instances is instances_to_add
    mock_repo.collection.insert_many.assert_called_once_with(instances_to_add)


def test_motor_repo_count(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for count operation."""
    expected_count = 1
    monkeypatch.setattr(mock_repo.collection, "count_documents", Mock(return_value=expected_count))
    count = mock_repo.count()
    assert count == expected_count
    mock_repo.collection.count_documents.assert_called_once_with({})


def test_motor_repo_count_with_custom_kwargs(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for count operation with custom kwargs."""
    expected_count = 1
    monkeypatch.setattr(mock_repo.collection, "count_documents", Mock(return_value=expected_count))
    count = mock_repo.count(foo="bar")
    assert count == expected_count
    mock_repo.collection.count_documents.assert_called_once_with({"foo": "bar"})


def test_motor_repo_count_with_filter(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for count operation with filter."""
    expected_count = 1
    monkeypatch.setattr(mock_repo.collection, "count_documents", Mock(return_value=expected_count))
    field_name = "updated_at"

    count = mock_repo.count(BeforeAfter(field_name, datetime.max, datetime.min))

    assert count == expected_count
    mock_repo.collection.count_documents.assert_called_once_with(
        {field_name: {"$lt": datetime.max, "$gt": datetime.min}}
    )


def test_motor_repo_delete(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for delete operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find_one_and_delete", Mock(return_value=expected_document))

    document = mock_repo.delete(expected_id)

    assert document is expected_document
    mock_repo.collection.find_one_and_delete.assert_called_once_with({"_id": expected_id})


def test_motor_repo_delete_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for delete operation when document is not found."""
    monkeypatch.setattr(mock_repo.collection, "find_one_and_delete", Mock(return_value=None))

    with pytest.raises(NotFoundError):
        mock_repo.delete(1)


def test_motor_repo_delete_many(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for delete many operation."""
    expected_ids = [1, 2, 3]
    expected_documents = [{"_id": expected_id} for expected_id in expected_ids]
    monkeypatch.setattr(mock_repo.collection, "find", Mock(return_value=MockCursor(return_value=expected_documents)))

    deleted_documents = mock_repo.delete_many(expected_ids)

    assert deleted_documents == expected_documents
    mock_repo.collection.find.assert_called_once_with({"_id": {"$in": expected_ids}})
    mock_repo.collection.delete_many.assert_called_once_with({"_id": {"$in": expected_ids}})


def test_motor_repo_exists(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for exists operation."""
    monkeypatch.setattr(mock_repo, "count", Mock(return_value=1))

    exists = mock_repo.exists(_id=1)

    assert exists
    mock_repo.count.assert_called_once_with(_id=1)


def test_motor_repo_exists_when_does_not_exist(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for exists operation when document does not exist."""
    monkeypatch.setattr(mock_repo, "count", Mock(return_value=0))

    exists = mock_repo.exists(_id=1)

    assert not exists
    mock_repo.count.assert_called_once_with(_id=1)


def test_motor_repo_get(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=expected_document))

    document = mock_repo.get(item_id=expected_id)

    assert document is expected_document
    mock_repo.collection.find_one.assert_called_once_with({"_id": expected_id})


def test_motor_repo_get_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get operation when document is not found."""
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=None))

    with pytest.raises(NotFoundError):
        mock_repo.get(1)


def test_motor_repo_get_one(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get one operation."""
    expected_document = {"_id": 1}
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=expected_document))
    filter = {"_id": 1}

    document = mock_repo.get_one(**filter)

    assert document is expected_document
    mock_repo.collection.find_one.assert_called_once_with(filter)


def test_motor_repo_get_one_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get one operation when document is not found."""
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=None))

    with pytest.raises(NotFoundError):
        mock_repo.get_one(_id=1)


def test_motor_repo_get_or_create_when_does_exist_and_no_upsert(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for get or create operation when document exists and we want don't to upsert."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo, "get_one_or_none", Mock(return_value=expected_document))

    document, created = mock_repo.get_or_create(_id=expected_id, upsert=False)

    assert document is expected_document
    assert not created
    mock_repo.get_one_or_none.assert_called_once_with(_id=expected_id)


def test_motor_repo_get_or_create_when_does_exist_and_upsert(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for get or create operation when document exists and we want to upsert."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo, "get_one_or_none", Mock(return_value=expected_document))
    monkeypatch.setattr(mock_repo.collection, "find_one_and_update", Mock(return_value=expected_document))

    document, created = mock_repo.get_or_create(_id=expected_id, upsert=True)

    assert document is expected_document
    assert not created
    mock_repo.get_one_or_none.assert_called_once_with(_id=expected_id)
    mock_repo.collection.find_one_and_update.assert_called_once_with(
        {"_id": expected_id}, {"$set": {"_id": expected_id}}, return_document=True
    )


def test_motor_repo_get_or_create_when_does_not_exist(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for get or create operation when document does not exist."""
    expected_id = 1
    created_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo, "get_one_or_none", Mock(return_value=None))
    monkeypatch.setattr(mock_repo, "add", Mock(return_value=created_document))
    filter_value = 2

    document, created = mock_repo.get_or_create(custom_filter=filter_value, upsert=True)

    assert document is created_document
    assert created
    mock_repo.get_one_or_none.assert_called_once_with(custom_filter=filter_value)
    mock_repo.add.assert_called_once_with({"custom_filter": filter_value})


def test_motor_repo_get_one_or_none(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get or none operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=expected_document))

    document = mock_repo.get_one_or_none(_id=expected_id)

    assert document is expected_document
    mock_repo.collection.find_one.assert_called_once_with({"_id": expected_id})


def test_motor_repo_get_one_or_none_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for get or none operation when document is not found."""
    expected_id = 1
    monkeypatch.setattr(mock_repo.collection, "find_one", Mock(return_value=None))

    document = mock_repo.get_one_or_none(_id=expected_id)

    assert document is None
    mock_repo.collection.find_one.assert_called_once_with({"_id": expected_id})


def test_motor_repo_update(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for update operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find_one_and_update", Mock(return_value=expected_document))

    document = mock_repo.update(expected_document)

    assert document is expected_document
    mock_repo.collection.find_one_and_update.assert_called_once_with(
        {"_id": expected_id}, {"$set": expected_document}, return_document=True
    )


def test_motor_repo_update_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for update operation when document is not found."""
    expected_document = {"_id": 1}
    monkeypatch.setattr(mock_repo.collection, "find_one_and_update", Mock(return_value=None))

    with pytest.raises(NotFoundError):
        mock_repo.update(expected_document)


def test_motor_repo_update_many(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for update many operation."""
    doc = {"_id": 1, "extra_data": 2}
    docs_to_update = [doc]
    bulk_write_result = Mock(matched_count=len(docs_to_update))
    monkeypatch.setattr(mock_repo.collection, "bulk_write", Mock(return_value=bulk_write_result))

    return_value = mock_repo.update_many(docs_to_update)

    assert return_value is docs_to_update
    mock_repo.collection.bulk_write.assert_called_once_with([UpdateOne({"_id": doc["_id"]}, {"$set": doc})])


def test_motor_repo_update_many_when_not_found(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for update many operation when no documents are found."""
    doc = {"_id": 1, "extra_data": 2}
    docs_to_update = [doc]
    bulk_write_result = Mock(matched_count=0)
    monkeypatch.setattr(mock_repo.collection, "bulk_write", Mock(return_value=bulk_write_result))

    with pytest.raises(NotFoundError):
        mock_repo.update_many(docs_to_update)


def test_motor_repo_upsert(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for upsert operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find_one_and_update", Mock(return_value=expected_document))
    document = mock_repo.upsert(expected_document)
    assert document is expected_document
    mock_repo.collection.find_one_and_update.assert_called_once_with(
        {"_id": expected_id}, {"$set": expected_document}, return_document=True
    )


def test_motor_repo_list_and_count(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for upsert list and count operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find", Mock(return_value=MockCursor([expected_document])))
    docs, count = mock_repo.list_and_count()
    assert docs == [expected_document]
    assert count == 1


def test_motor_repo_list(mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch) -> None:
    """Test expected method calls for list operation."""
    expected_id = 1
    expected_document = {"_id": expected_id}
    monkeypatch.setattr(mock_repo.collection, "find", Mock(return_value=MockCursor([expected_document])))
    docs = mock_repo.list()
    assert docs == [expected_document]


def test_motor_repo_build_query_from_filters_for_before_after_filter(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for build query from filters operation for BeforeAfter filter."""
    before_date = datetime.now()
    after_date = datetime.now()
    filter = mock_repo._build_query_from_filters(BeforeAfter(field_name="field", before=before_date, after=after_date))
    assert filter == {"field": {"$lt": before_date, "$gt": after_date}}


def test_motor_repo_build_query_from_filters_for_collection_filter(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for build query from filters operation for CollectionFilter."""
    filter = mock_repo._build_query_from_filters(CollectionFilter(field_name="field", values=[1, 2]))
    assert filter == {"field": {"$in": [1, 2]}}


def test_motor_repo_build_query_from_filters_for_search_filter_with_ignore_case(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for build query from filters operation for SearchFilter with ignore case."""
    filter = mock_repo._build_query_from_filters(SearchFilter(field_name="field", value="value", ignore_case=True))
    assert filter == {"field": {"$regex": "value", "$options": "i"}}


def test_motor_repo_build_query_from_filters_for_search_filter_without_ignore_case(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for build query from filters operation for SearchFilter without ignore case."""
    filter = mock_repo._build_query_from_filters(SearchFilter(field_name="field", value="value", ignore_case=False))
    assert filter == {"field": {"$regex": "value"}}


def test_motor_repo_build_query_from_filters_for_incompatible_filters(
    mock_repo: MongoDbSyncRepository, monkeypatch: MonkeyPatch
) -> None:
    """Test expected method calls for build query from filters operation for incompatible filters."""
    incompatible_filters: List[FilterTypes] = [LimitOffset(1, 1), OrderBy("field", "asc")]
    for incompatible_filter in incompatible_filters:
        with pytest.raises(RepositoryError):
            mock_repo._build_query_from_filters(incompatible_filter)
