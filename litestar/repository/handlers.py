from typing import TYPE_CHECKING, Any, Callable, Dict

from litestar.utils import warn_deprecation

__all__ = ("on_app_init", "signature_namespace_values")


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        try:
            from advanced_alchemy import filters as _filters_source
        except ImportError:  # pragma: no cover
            from litestar.repository import _filters as _filters_source  # type: ignore[no-redef]

        signature_namespace_values: Dict[str, Any] = {
            "BeforeAfter": _filters_source.BeforeAfter,
            "OnBeforeAfter": _filters_source.OnBeforeAfter,
            "CollectionFilter": _filters_source.CollectionFilter,
            "LimitOffset": _filters_source.LimitOffset,
            "OrderBy": _filters_source.OrderBy,
            "SearchFilter": _filters_source.SearchFilter,
            "NotInCollectionFilter": _filters_source.NotInCollectionFilter,
            "NotInSearchFilter": _filters_source.NotInSearchFilter,
            "FilterTypes": _filters_source.FilterTypes,
        }

        def on_app_init(app_config: "AppConfig") -> "AppConfig":
            """Add custom filters for the application during signature modelling."""

            app_config.signature_namespace.update(signature_namespace_values)
            return app_config

        warn_deprecation(
            deprecated_name=f"litestar.repository.handlers.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            info=f"importing {attr_name} from 'litestar.repository.handlers' is deprecated. There is "
            f"no direct replacement; wire the filter signature namespace yourself, or use "
            f"'advanced_alchemy.extensions.litestar.SQLAlchemyPlugin' which registers it for you.",
        )

        value: object = signature_namespace_values if attr_name == "signature_namespace_values" else on_app_init
        globals()[attr_name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    signature_namespace_values: Dict[str, Any]
    on_app_init: Callable[[AppConfig], AppConfig]
