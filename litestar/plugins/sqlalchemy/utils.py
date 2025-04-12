from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.utils.__all__ (inferred: the module itself)
_EXPORTED_SYMBOLS = {
    "text",
    "singleton",
    "sync_tools",
    "module_loader",
    "portals",
    "dataclass",
    "deprecation",
}

_SOURCE_MODULE = "advanced_alchemy.utils"


def __getattr__(name: str) -> Any:
    """Load symbols lazily from the underlying Advanced Alchemy module."""
    # This implementation assumes utils.py in Litestar should re-export
    # the entire advanced_alchemy.utils module when `utils` is accessed.
    if name == "utils":  # Special case based on .pyi
        module = importlib.import_module(_SOURCE_MODULE)
        globals()[name] = module
        return module
    # Add other specific symbol lookups here if utils.py
    # is intended to export more than just the module `utils`

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.utils import (  # noqa: F401
        dataclass,  # pyright: ignore
        deprecation,  # pyright: ignore
        module_loader,  # pyright: ignore
        portals,  # pyright: ignore
        singleton,  # pyright: ignore
        sync_tools,  # pyright: ignore
        text,  # pyright: ignore
    )
