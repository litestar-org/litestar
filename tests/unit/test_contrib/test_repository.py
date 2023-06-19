from litestar.app import Litestar
from litestar.contrib.repository import handlers
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, LimitOffset, OrderBy, SearchFilter


def test_app_debug_create_logger() -> None:
    app = Litestar([], on_app_init=[handlers.on_app_init])

    assert app.signature_namespace == {
        "BeforeAfter": BeforeAfter,
        "CollectionFilter": CollectionFilter,
        "LimitOffset": LimitOffset,
        "OrderBy": OrderBy,
        "SearchFilter": SearchFilter,
    }
