from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.filters.__all__
_EXPORTED_SYMBOLS = {
    "BeforeAfter",
    "CollectionFilter",
    "ComparisonFilter",
    "ExistsFilter",
    "FilterGroup",
    "FilterMap",
    "FilterTypes",
    "InAnyFilter",
    "LimitOffset",
    "LogicalOperatorMap",
    "MultiFilter",
    "NotExistsFilter",
    "NotInCollectionFilter",
    "NotInSearchFilter",
    "OnBeforeAfter",
    "OrderBy",
    "PaginationFilter",
    "SearchFilter",
    "StatementFilter",
    "StatementFilterT",  # Type Alias
    "StatementTypeT",  # Type Alias
}

_SOURCE_MODULE = "advanced_alchemy.filters"


def __getattr__(name: str) -> Any:
    """Load symbols lazily from the underlying Advanced Alchemy module."""
    if name in _EXPORTED_SYMBOLS:
        module = importlib.import_module(_SOURCE_MODULE)
        attr = getattr(module, name)
        # Cache it in the current module's globals
        globals()[name] = attr
        return attr

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Define __all__ statically based on the symbols being lazy-loaded
__all__ = (
    "BeforeAfter",
    "CollectionFilter",
    "ComparisonFilter",
    "ExistsFilter",
    "FilterGroup",
    "FilterMap",
    "FilterTypes",  # Type Alias
    "InAnyFilter",
    "LimitOffset",
    "LogicalOperatorMap",
    "MultiFilter",
    "NotExistsFilter",
    "NotInCollectionFilter",
    "NotInSearchFilter",
    "OnBeforeAfter",
    "OrderBy",
    "PaginationFilter",
    "SearchFilter",
    "StatementFilter",
    "StatementFilterT",  # Type Alias
    "StatementTypeT",  # Type Alias
)

if TYPE_CHECKING:
    from advanced_alchemy.filters import (
        BeforeAfter,
        CollectionFilter,
        ComparisonFilter,
        ExistsFilter,
        FilterGroup,
        FilterMap,
        FilterTypes,
        InAnyFilter,
        LimitOffset,
        LogicalOperatorMap,
        MultiFilter,
        NotExistsFilter,
        NotInCollectionFilter,
        NotInSearchFilter,
        OnBeforeAfter,
        OrderBy,
        PaginationFilter,
        SearchFilter,
        StatementFilter,
        StatementFilterT,
        StatementTypeT,
    )
