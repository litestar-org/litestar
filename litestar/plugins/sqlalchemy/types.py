from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.types.__all__
_EXPORTED_SYMBOLS = {
    "GUID",
    "NANOID_INSTALLED",
    "ORA_JSONB",
    "UUID_UTILS_INSTALLED",
    "BigIntIdentity",
    "DateTimeUTC",
    "EncryptedString",
    "EncryptedText",
    "EncryptionBackend",  # Protocol
    "FernetBackend",
    "FileObject",
    "FileObjectList",
    "JsonB",
    "MutableList",
    "PGCryptoBackend",
    "StorageBackend",  # Protocol
    "StorageBackendT",  # TypeVar
    "StorageRegistry",
    "StoredObject",
    "file_object",
    "storages",
}

_SOURCE_MODULE = "advanced_alchemy.types"


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
# Excluding Protocols/TypeVars from runtime __all__
__all__ = (
    "GUID",
    "NANOID_INSTALLED",
    "ORA_JSONB",
    "UUID_UTILS_INSTALLED",
    "BigIntIdentity",
    "DateTimeUTC",
    "EncryptedString",
    "EncryptedText",
    "EncryptionBackend",
    "FernetBackend",
    "FileObject",
    "FileObjectList",
    "JsonB",
    "MutableList",
    "PGCryptoBackend",
    "StorageBackend",
    "StorageBackendT",
    "StorageRegistry",
    "StoredObject",
    "file_object",
    "storages",
)

if TYPE_CHECKING:
    from advanced_alchemy.types import (
        GUID,
        NANOID_INSTALLED,
        ORA_JSONB,
        UUID_UTILS_INSTALLED,
        BigIntIdentity,
        DateTimeUTC,
        EncryptedString,
        EncryptedText,
        EncryptionBackend,
        FernetBackend,
        FileObject,
        FileObjectList,
        JsonB,
        MutableList,
        PGCryptoBackend,
        StorageBackend,
        StorageBackendT,
        StorageRegistry,
        StoredObject,
        file_object,
        storages,
    )
