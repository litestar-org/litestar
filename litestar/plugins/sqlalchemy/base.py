from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.base.__all__
_EXPORTED_SYMBOLS = {
    "AdvancedDeclarativeBase",
    "BasicAttributes",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntBaseT",
    "CommonTableAttributes",
    "DefaultBase",
    "ModelProtocol",
    "NanoIDAuditBase",
    "NanoIDBase",
    "NanoIDBaseT",
    "SQLQuery",
    "TableArgsType",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDBaseT",
    "UUIDv6AuditBase",
    "UUIDv6Base",
    "UUIDv6BaseT",
    "UUIDv7AuditBase",
    "UUIDv7Base",
    "UUIDv7BaseT",
    "convention",
    "create_registry",
    "merge_table_arguments",
    "metadata_registry",
    "orm_registry",
    "table_name_regexp",
}

_SOURCE_MODULE = "advanced_alchemy.base"


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
# Exclude TypeVars from runtime __all__
__all__ = (
    "AdvancedDeclarativeBase",
    "BasicAttributes",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntBaseT",
    "CommonTableAttributes",
    "DefaultBase",
    "ModelProtocol",
    "NanoIDAuditBase",
    "NanoIDBase",
    "NanoIDBaseT",
    "SQLQuery",
    "TableArgsType",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDBaseT",
    "UUIDv6AuditBase",
    "UUIDv6Base",
    "UUIDv6BaseT",
    "UUIDv7AuditBase",
    "UUIDv7Base",
    "UUIDv7BaseT",
    "convention",
    "create_registry",
    "merge_table_arguments",
    "metadata_registry",
    "orm_registry",
    "table_name_regexp",
)
if TYPE_CHECKING:
    from advanced_alchemy.base import (
        AdvancedDeclarativeBase,
        BasicAttributes,
        BigIntAuditBase,
        BigIntBase,
        BigIntBaseT,
        CommonTableAttributes,
        DefaultBase,
        ModelProtocol,
        NanoIDAuditBase,
        NanoIDBase,
        NanoIDBaseT,
        SQLQuery,
        TableArgsType,
        UUIDAuditBase,
        UUIDBase,
        UUIDBaseT,
        UUIDv6AuditBase,
        UUIDv6Base,
        UUIDv6BaseT,
        UUIDv7AuditBase,
        UUIDv7Base,
        UUIDv7BaseT,
        convention,
        create_registry,
        merge_table_arguments,
        metadata_registry,
        orm_registry,
        table_name_regexp,
    )
