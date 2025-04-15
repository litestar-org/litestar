import importlib
from typing import TYPE_CHECKING, Any

# Map symbols to the module they are defined in (for lazy loading)
_LAZY_LOAD_MAP = {
    # Symbols from advanced_alchemy.extensions.litestar
    "AlembicAsyncConfig": "advanced_alchemy.extensions.litestar",
    "AlembicCommands": "advanced_alchemy.extensions.litestar",
    "AlembicSyncConfig": "advanced_alchemy.extensions.litestar",
    "AsyncSessionConfig": "advanced_alchemy.extensions.litestar",
    "EngineConfig": "advanced_alchemy.extensions.litestar",
    "SQLAlchemyAsyncConfig": "advanced_alchemy.extensions.litestar",
    "SQLAlchemyDTO": "advanced_alchemy.extensions.litestar",
    "SQLAlchemyDTOConfig": "advanced_alchemy.extensions.litestar",
    "SQLAlchemyInitPlugin": "advanced_alchemy.extensions.litestar",
    "SQLAlchemyPlugin": "advanced_alchemy.extensions.litestar",
    "SQLAlchemySerializationPlugin": "advanced_alchemy.extensions.litestar",
    "SQLAlchemySyncConfig": "advanced_alchemy.extensions.litestar",
    "SyncSessionConfig": "advanced_alchemy.extensions.litestar",
    "async_autocommit_before_send_handler": "advanced_alchemy.extensions.litestar",
    "async_autocommit_handler_maker": "advanced_alchemy.extensions.litestar",
    "async_default_before_send_handler": "advanced_alchemy.extensions.litestar",
    "async_default_handler_maker": "advanced_alchemy.extensions.litestar",
    "get_database_migration_plugin": "advanced_alchemy.extensions.litestar",
    "providers": "advanced_alchemy.extensions.litestar",  # Assuming providers is only in extensions
    "sync_autocommit_before_send_handler": "advanced_alchemy.extensions.litestar",
    "sync_autocommit_handler_maker": "advanced_alchemy.extensions.litestar",
    "sync_default_before_send_handler": "advanced_alchemy.extensions.litestar",
    "sync_default_handler_maker": "advanced_alchemy.extensions.litestar",
    # Modules from advanced_alchemy top-level
    "base": "advanced_alchemy.base",
    "exceptions": "advanced_alchemy.exceptions",
    "filters": "advanced_alchemy.filters",
    "mixins": "advanced_alchemy.mixins",
    "operations": "advanced_alchemy.operations",
    "repository": "advanced_alchemy.repository",
    "service": "advanced_alchemy.service",
    "types": "advanced_alchemy.types",
    "utils": "advanced_alchemy.utils",
}

if TYPE_CHECKING:
    # Eagerly import modules and specific symbols for type checkers
    from advanced_alchemy import (
        base,
        exceptions,
        filters,
        mixins,
        operations,
        repository,
        service,
        types,
        utils,
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
        get_database_migration_plugin,
        providers,
        sync_autocommit_before_send_handler,
        sync_autocommit_handler_maker,
        sync_default_before_send_handler,
        sync_default_handler_maker,
    )


def __getattr__(name: str) -> Any:
    """Load symbols/modules lazily from advanced_alchemy or its extensions."""
    if name in _LAZY_LOAD_MAP:
        module_path = _LAZY_LOAD_MAP[name]
        # Check if we are loading a module itself (e.g., 'base') or a symbol from a module
        if name == module_path.split(".")[-1]:
            # Loading the module itself
            module = importlib.import_module(module_path)
            globals()[name] = module  # Cache the module
            return module
        # Loading a specific symbol from a module
        module = importlib.import_module(module_path)
        attr = getattr(module, name)
        globals()[name] = attr  # Cache the symbol
        return attr

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Define __all__ statically based on the symbols and modules being lazy-loaded
__all__ = (
    # Symbols from extensions
    "AlembicAsyncConfig",
    "AlembicCommands",
    "AlembicSyncConfig",
    "AsyncSessionConfig",
    "EngineConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyDTO",
    "SQLAlchemyDTOConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
    "async_autocommit_before_send_handler",
    "async_autocommit_handler_maker",
    "async_default_before_send_handler",
    "async_default_handler_maker",
    # Modules from top-level
    "base",
    "exceptions",
    "filters",
    "get_database_migration_plugin",
    "mixins",
    "operations",
    "providers",
    "repository",
    "service",
    "sync_autocommit_before_send_handler",
    "sync_autocommit_handler_maker",
    "sync_default_before_send_handler",
    "sync_default_handler_maker",
    "types",
    "utils",
)
