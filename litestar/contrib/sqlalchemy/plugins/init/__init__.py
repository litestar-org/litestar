from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AsyncSessionConfig",
    "EngineConfig",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
)

def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name in (    "GenericSQLAlchemyConfig",    "GenericSessionConfig"):
            module = "litestar.plugins.sqlalchemy.config"
            from advanced_alchemy.config import (  # pyright: ignore[reportMissingImports]
                GenericSessionConfig,
                GenericSQLAlchemyConfig, 
            )
            value = globals()[attr_name] = locals()[attr_name]
        else:
            module = "litestar.plugins.sqlalchemy.config"
            from advanced_alchemy.extensions.litestar.plugins.init import (
                AsyncSessionConfig,
                EngineConfig, 
                SQLAlchemyAsyncConfig,
                SQLAlchemyInitPlugin,
                SQLAlchemySyncConfig,
                SyncSessionConfig,
        )
            value = globals()[attr_name] = locals()[attr_name]
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.{attr_name}",
            version="2.11",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated, please "
            f"import it from '{module}' instead",
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.plugins.init import (
        AsyncSessionConfig,
        EngineConfig,
        GenericSessionConfig,
        GenericSQLAlchemyConfig,
        SQLAlchemyAsyncConfig,
        SQLAlchemyInitPlugin,
        SQLAlchemySyncConfig,
        SyncSessionConfig,
    )
