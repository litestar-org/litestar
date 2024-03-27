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
