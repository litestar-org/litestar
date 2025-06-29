# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
"""SQLAlchemy plugin for Litestar."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import TYPE_CHECKING, Any

from litestar.exceptions import MissingDependencyException

__all__ = (
    "AlembicAsyncConfig",
    "AlembicCommands",
    "AlembicSyncConfig",
    "AsyncSessionConfig",
    "AuditColumns",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntPrimaryKey",
    "CommonTableAttributes",
    "EngineConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyDTO",
    "SQLAlchemyDTOConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDPrimaryKey",
    "async_autocommit_before_send_handler",
    "async_autocommit_handler_maker",
    "async_default_before_send_handler",
    "async_default_handler_maker",
    "base",
    "dto",
    "exceptions",
    "filters",
    "get_database_migration_plugin",
    "mixins",
    "operations",
    "orm_registry",
    "repository",
    "service",
    "sync_autocommit_before_send_handler",
    "sync_autocommit_handler_maker",
    "sync_default_before_send_handler",
    "sync_default_handler_maker",
    "types",
    "utils",
)

# Advanced Alchemy submodules that should be dynamically created
_ADVANCED_ALCHEMY_SUBMODULES = {
    "filters",
    "mixins",
    "operations",
    "service",
    "types",
    "utils",
}

# Try to import advanced_alchemy, providing helpful error if not available
try:
    # Import everything from advanced_alchemy.extensions.litestar explicitly
    # Also import additional base classes and mixins we re-export
    from advanced_alchemy.base import (
        BigIntAuditBase,
        BigIntBase,
        CommonTableAttributes,
        UUIDAuditBase,
        UUIDBase,
        orm_registry,
    )
    from advanced_alchemy.extensions.litestar import (
        AlembicAsyncConfig,
        AlembicCommands,
        AlembicSyncConfig,
        AsyncSessionConfig,
        EngineConfig,
        SQLAlchemyAsyncConfig,
        SQLAlchemyDTO,
        SQLAlchemyDTOConfig,
        SQLAlchemyInitPlugin,
        SQLAlchemyPlugin,
        SQLAlchemySerializationPlugin,
        SQLAlchemySyncConfig,
        SyncSessionConfig,
        async_autocommit_before_send_handler,
        async_autocommit_handler_maker,
        async_default_before_send_handler,
        async_default_handler_maker,
        base,
        exceptions,
        filters,
        get_database_migration_plugin,
        mixins,
        operations,
        repository,
        service,
        sync_autocommit_before_send_handler,
        sync_autocommit_handler_maker,
        sync_default_before_send_handler,
        sync_default_handler_maker,
        types,
        utils,
    )
    from advanced_alchemy.mixins import (
        AuditColumns,
        BigIntPrimaryKey,
        UUIDPrimaryKey,
    )
except ImportError as e:
    raise MissingDependencyException("advanced-alchemy", extra="sqlalchemy") from e

# Import our own submodules with aliases to avoid conflicts
from . import base as _local_base
from . import dto
from . import exceptions as _local_exceptions
from . import repository as _local_repository

# Override the advanced_alchemy imports with our local ones
base = _local_base
exceptions = _local_exceptions
repository = _local_repository


def _create_dynamic_submodule(submodule_name: str) -> ModuleType:
    """Create a dynamic submodule that proxies to advanced_alchemy.extensions.litestar."""
    import advanced_alchemy.extensions.litestar as litestar_ext

    # Get the corresponding module from advanced_alchemy.extensions.litestar
    advanced_module = getattr(litestar_ext, submodule_name)

    # Create a new module
    full_name = f"{__name__}.{submodule_name}"
    dynamic_module = ModuleType(full_name)
    dynamic_module.__file__ = __file__
    if hasattr(sys.modules[__name__], "__loader__"):
        dynamic_module.__loader__ = sys.modules[__name__].__loader__
    dynamic_module.__package__ = __name__

    # Add __getattr__ to proxy attribute access
    def __getattr__(name: str) -> Any:
        try:
            return getattr(advanced_module, name)
        except AttributeError:
            raise AttributeError(f"module {full_name!r} has no attribute {name!r}") from None

    def __dir__() -> list[str]:
        return [name for name in dir(advanced_module) if not name.startswith("_")]

    setattr(dynamic_module, "__getattr__", __getattr__)
    setattr(dynamic_module, "__dir__", __dir__)

    # Make all public attributes directly accessible
    for attr_name in dir(advanced_module):
        if not attr_name.startswith("_"):
            setattr(dynamic_module, attr_name, getattr(advanced_module, attr_name))

    return dynamic_module


# Pre-register all dynamic submodules in sys.modules to support direct imports
for _submodule_name in _ADVANCED_ALCHEMY_SUBMODULES:
    _dynamic_submodule = _create_dynamic_submodule(_submodule_name)
    sys.modules[f"{__name__}.{_submodule_name}"] = _dynamic_submodule
    globals()[_submodule_name] = _dynamic_submodule


def __getattr__(name: str) -> Any:
    """Handle module-level attribute access for submodules."""
    if name in __all__:
        return globals().get(name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    # Re-export for type checking
    from advanced_alchemy.extensions.litestar import (
        filters,
        mixins,
        operations,
        service,
        types,
        utils,
    )

    from . import base as base
    from . import dto as dto
    from . import exceptions as exceptions
    from . import repository as repository
