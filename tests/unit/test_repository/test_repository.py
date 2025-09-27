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
