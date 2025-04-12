from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.repository.__all__ (inferred from .pyi)
# Includes symbols from _async, _sync, _util, typing
_EXPORTED_SYMBOLS = {
    "DEFAULT_ERROR_MESSAGE_TEMPLATES",
    "Empty",
    "EmptyType",
    "ErrorMessages",
    "FilterableRepository",
    "FilterableRepositoryProtocol",
    "LoadSpec",
    "ModelOrRowMappingT",  # Type Alias
    "ModelT",  # TypeVar
    "OrderingPair",  # Type Alias
    "SQLAlchemyAsyncQueryRepository",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemyAsyncRepositoryProtocol",
    "SQLAlchemyAsyncSlugRepository",
    "SQLAlchemyAsyncSlugRepositoryProtocol",
    "SQLAlchemySyncQueryRepository",
    "SQLAlchemySyncRepository",
    "SQLAlchemySyncRepositoryProtocol",
    "SQLAlchemySyncSlugRepository",
    "SQLAlchemySyncSlugRepositoryProtocol",
    "get_instrumented_attr",
    "model_from_dict",
}

# Determine the source module based on the symbol name
_SOURCE_MODULE_MAP = dict.fromkeys(
    {
        "SQLAlchemyAsyncQueryRepository",
        "SQLAlchemyAsyncRepository",
        "SQLAlchemyAsyncRepositoryProtocol",
        "SQLAlchemyAsyncSlugRepository",
        "SQLAlchemyAsyncSlugRepositoryProtocol",
    },
    "advanced_alchemy.repository._async",
)
_SOURCE_MODULE_MAP.update(
    dict.fromkeys(
        {
            "SQLAlchemySyncQueryRepository",
            "SQLAlchemySyncRepository",
            "SQLAlchemySyncRepositoryProtocol",
            "SQLAlchemySyncSlugRepository",
            "SQLAlchemySyncSlugRepositoryProtocol",
        },
        "advanced_alchemy.repository._sync",
    )
)
_SOURCE_MODULE_MAP.update(
    dict.fromkeys(
        {
            "DEFAULT_ERROR_MESSAGE_TEMPLATES",
            "FilterableRepository",
            "FilterableRepositoryProtocol",
            "LoadSpec",
            "get_instrumented_attr",
            "model_from_dict",
        },
        "advanced_alchemy.repository._util",
    )
)
_SOURCE_MODULE_MAP.update(
    dict.fromkeys({"ModelOrRowMappingT", "ModelT", "OrderingPair"}, "advanced_alchemy.repository.typing")
)
_SOURCE_MODULE_MAP.update(dict.fromkeys({"Empty", "EmptyType"}, "advanced_alchemy.utils.dataclass"))
_SOURCE_MODULE_MAP["ErrorMessages"] = "advanced_alchemy.exceptions"  # Mapped from exceptions


def __getattr__(name: str) -> Any:
    """Load symbols lazily from the underlying Advanced Alchemy modules."""
    if name in _EXPORTED_SYMBOLS:
        try:
            module_path = _SOURCE_MODULE_MAP[name]
        except KeyError:
            # Fallback or raise more specific error if needed
            raise AttributeError(f"Source module not mapped for lazy loading symbol: {name!r}") from None

        module = importlib.import_module(module_path)
        attr = getattr(module, name)
        # Cache it in the current module's globals
        globals()[name] = attr
        return attr

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Define __all__ statically based on the symbols being lazy-loaded
# Exclude TypeVars/Aliases if not intended for runtime use, but keeping for now based on pyi
__all__ = (
    "DEFAULT_ERROR_MESSAGE_TEMPLATES",
    "Empty",
    "EmptyType",
    "ErrorMessages",
    "FilterableRepository",
    "FilterableRepositoryProtocol",
    "LoadSpec",
    "ModelOrRowMappingT",
    "ModelT",
    "OrderingPair",
    "SQLAlchemyAsyncQueryRepository",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemyAsyncRepositoryProtocol",
    "SQLAlchemyAsyncSlugRepository",
    "SQLAlchemyAsyncSlugRepositoryProtocol",
    "SQLAlchemySyncQueryRepository",
    "SQLAlchemySyncRepository",
    "SQLAlchemySyncRepositoryProtocol",
    "SQLAlchemySyncSlugRepository",
    "SQLAlchemySyncSlugRepositoryProtocol",
    "get_instrumented_attr",
    "model_from_dict",
)

if TYPE_CHECKING:
    from advanced_alchemy.repository import (
        DEFAULT_ERROR_MESSAGE_TEMPLATES,
        Empty,
        EmptyType,
        ErrorMessages,
        FilterableRepository,
        FilterableRepositoryProtocol,
        LoadSpec,
        ModelOrRowMappingT,
        ModelT,
        OrderingPair,
        SQLAlchemyAsyncQueryRepository,
        SQLAlchemyAsyncRepository,
        SQLAlchemyAsyncRepositoryProtocol,
        SQLAlchemyAsyncSlugRepository,
        SQLAlchemyAsyncSlugRepositoryProtocol,
        SQLAlchemySyncQueryRepository,
        SQLAlchemySyncRepository,
        SQLAlchemySyncRepositoryProtocol,
        SQLAlchemySyncSlugRepository,
        SQLAlchemySyncSlugRepositoryProtocol,
        get_instrumented_attr,
        model_from_dict,
    )
