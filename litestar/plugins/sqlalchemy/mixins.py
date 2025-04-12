from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.mixins.__all__
_EXPORTED_SYMBOLS = {
    "AuditColumns",
    "BigIntPrimaryKey",
    "NanoIDPrimaryKey",
    "SentinelMixin",
    "SlugKey",
    "UUIDPrimaryKey",
    "UUIDv6PrimaryKey",
    "UUIDv7PrimaryKey",
    "UniqueMixin",
}

_SOURCE_MODULE = "advanced_alchemy.mixins"


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
    "AuditColumns",
    "BigIntPrimaryKey",
    "NanoIDPrimaryKey",
    "SentinelMixin",
    "SlugKey",
    "UUIDPrimaryKey",
    "UUIDv6PrimaryKey",
    "UUIDv7PrimaryKey",
    "UniqueMixin",
)

if TYPE_CHECKING:
    from advanced_alchemy.mixins import (
        AuditColumns,
        BigIntPrimaryKey,
        NanoIDPrimaryKey,
        SentinelMixin,
        SlugKey,
        UniqueMixin,
        UUIDPrimaryKey,
        UUIDv6PrimaryKey,
        UUIDv7PrimaryKey,
    )
