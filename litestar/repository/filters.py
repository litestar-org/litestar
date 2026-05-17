from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "BeforeAfter",
    "CollectionFilter",
    "FilterTypes",
    "LimitOffset",
    "NotInCollectionFilter",
    "NotInSearchFilter",
    "OnBeforeAfter",
    "OrderBy",
    "SearchFilter",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        try:
            from advanced_alchemy import filters as _filters_source
        except ImportError:  # pragma: no cover
            from litestar.repository import _filters as _filters_source  # type: ignore[no-redef]

        warn_deprecation(
            deprecated_name=f"litestar.repository.filters.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            alternative=f"advanced_alchemy.filters.{attr_name}",
            info=f"importing {attr_name} from 'litestar.repository.filters' is deprecated, please "
            f"import it from 'advanced_alchemy.filters' instead",
        )

        value = globals()[attr_name] = getattr(_filters_source, attr_name)
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.filters import (
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
