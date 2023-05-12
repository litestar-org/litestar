from typing import TYPE_CHECKING

from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, LimitOffset, OrderBy, SearchFilter

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


signature_namespace_values = {
    "BeforeAfter": BeforeAfter,
    "CollectionFilter": CollectionFilter,
    "LimitOffset": LimitOffset,
    "OrderBy": OrderBy,
    "SearchFilter": SearchFilter,
}


def on_app_init(app_config: "AppConfig") -> "AppConfig":
    """Add custom filters for the application during signature modelling."""

    app_config.signature_namespace.update(signature_namespace_values)
    return app_config
