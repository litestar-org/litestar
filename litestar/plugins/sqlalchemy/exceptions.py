from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.exceptions.__all__
_EXPORTED_SYMBOLS = {
    "AdvancedAlchemyError",
    "DuplicateKeyError",
    "ErrorMessages",
    "ForeignKeyError",
    "ImproperConfigurationError",
    "IntegrityError",
    "MissingDependencyError",
    "MultipleResultsFoundError",
    "NotFoundError",
    "RepositoryError",
    "SerializationError",
    "wrap_sqlalchemy_exception",
}

_SOURCE_MODULE = "advanced_alchemy.exceptions"


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
    "AdvancedAlchemyError",
    "DuplicateKeyError",
    "ErrorMessages",
    "ForeignKeyError",
    "ImproperConfigurationError",
    "IntegrityError",
    "MissingDependencyError",
    "MultipleResultsFoundError",
    "NotFoundError",
    "RepositoryError",
    "SerializationError",
    "wrap_sqlalchemy_exception",
)

if TYPE_CHECKING:
    from advanced_alchemy.exceptions import (
        AdvancedAlchemyError,
        DuplicateKeyError,
        ErrorMessages,
        ForeignKeyError,
        ImproperConfigurationError,
        IntegrityError,
        MissingDependencyError,
        MultipleResultsFoundError,
        NotFoundError,
        RepositoryError,
        SerializationError,
        wrap_sqlalchemy_exception,
    )
