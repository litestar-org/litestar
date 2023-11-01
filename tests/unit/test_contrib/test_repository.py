import pytest

from litestar.app import Litestar
from litestar.repository import handlers
from litestar.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    FilterTypes,
    LimitOffset,
    NotInCollectionFilter,
    NotInSearchFilter,
    OnBeforeAfter,
    OrderBy,
    SearchFilter,
)


def test_app_repository_signature_namespace() -> None:
    app = Litestar([], on_app_init=[handlers.on_app_init])

    assert app.signature_namespace == {
        "BeforeAfter": BeforeAfter,
        "OnBeforeAfter": OnBeforeAfter,
        "CollectionFilter": CollectionFilter,
        "LimitOffset": LimitOffset,
        "OrderBy": OrderBy,
        "SearchFilter": SearchFilter,
        "NotInCollectionFilter": NotInCollectionFilter,
        "NotInSearchFilter": NotInSearchFilter,
        "FilterTypes": FilterTypes,
    }


def test_deprecated_abc_imports() -> None:
    from litestar.contrib.repository import abc as abc_contrib
    from litestar.repository import abc

    assert abc_contrib.AbstractAsyncRepository is abc.AbstractAsyncRepository
    assert abc_contrib.AbstractSyncRepository is abc.AbstractSyncRepository

    with pytest.raises(AttributeError):
        abc_contrib.foo


def test_deprecated_exception_imports() -> None:
    from litestar.contrib.repository import exceptions as contrib_exceptions
    from litestar.repository import exceptions

    assert exceptions.RepositoryError is contrib_exceptions.RepositoryError
    assert exceptions.ConflictError is contrib_exceptions.ConflictError
    assert exceptions.NotFoundError is contrib_exceptions.NotFoundError

    with pytest.raises(AttributeError):
        contrib_exceptions.foo


def test_deprecated_filters_imports() -> None:
    from litestar.contrib.repository import filters as contrib_filter
    from litestar.repository import filters

    assert filters.FilterTypes is contrib_filter.FilterTypes
    assert filters.CollectionFilter is contrib_filter.CollectionFilter
    assert filters.NotInCollectionFilter is contrib_filter.NotInCollectionFilter
    assert filters.SearchFilter is contrib_filter.SearchFilter
    assert filters.NotInSearchFilter is contrib_filter.NotInSearchFilter
    assert filters.OnBeforeAfter is contrib_filter.OnBeforeAfter
    assert filters.BeforeAfter is contrib_filter.BeforeAfter
    assert filters.LimitOffset is contrib_filter.LimitOffset
    assert filters.OrderBy is contrib_filter.OrderBy

    with pytest.raises(AttributeError):
        contrib_filter.foo


def test_advanced_alchemy_imports() -> None:
    from advanced_alchemy import filters

    from litestar.repository import _filters

    assert filters.FilterTypes is not _filters.FilterTypes
    assert filters.CollectionFilter is not _filters.CollectionFilter
    assert filters.NotInCollectionFilter is not _filters.NotInCollectionFilter
    assert filters.SearchFilter is not _filters.SearchFilter
    assert filters.NotInSearchFilter is not _filters.NotInSearchFilter
    assert filters.OnBeforeAfter is not _filters.OnBeforeAfter
    assert filters.BeforeAfter is not _filters.BeforeAfter
    assert filters.LimitOffset is not _filters.LimitOffset
    assert filters.OrderBy is not _filters.OrderBy


def test_deprecated_handlers_imports() -> None:
    from litestar.contrib.repository import handlers as contrib_handlers
    from litestar.repository import handlers

    assert handlers.on_app_init is contrib_handlers.on_app_init

    with pytest.raises(AttributeError):
        contrib_handlers.foo


def test_deprecated_testing_imports() -> None:
    from litestar.contrib.repository import testing as contrib_testing
    from litestar.repository.testing import generic_mock_repository

    assert generic_mock_repository.GenericAsyncMockRepository is contrib_testing.GenericAsyncMockRepository
    assert generic_mock_repository.GenericSyncMockRepository is contrib_testing.GenericSyncMockRepository

    with pytest.raises(AttributeError):
        contrib_testing.foo
