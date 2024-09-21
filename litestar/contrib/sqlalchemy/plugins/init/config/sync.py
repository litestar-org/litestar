from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "SQLAlchemySyncConfig",
    "AlembicSyncConfig",
    "SyncSessionConfig",
    "default_before_send_handler",
    "autocommit_before_send_handler",
)

def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name == "SQLAlchemySyncConfig":
            from litestar.contrib.sqlalchemy.plugins.init.config.compat import _CreateEngineMixin
            from sqlalchemy import Engine
            from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
                SQLAlchemySyncConfig as _SQLAlchemySyncConfig,
            )

            class SQLAlchemySyncConfig(_SQLAlchemySyncConfig, _CreateEngineMixin[Engine]): ...

            value = globals()[attr_name] = SQLAlchemySyncConfig
        elif attr_name in {"default_before_send_handler", "autocommit_before_send_handler"}:
            module = "litestar.plugins.sqlalchemy.plugins.init.config.sync"
            from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
                default_before_send_handler,
                autocommit_before_send_handler,
            )

            value = globals()[attr_name] = locals()[attr_name]
        else:
            module = "litestar.plugins.sqlalchemy"
            from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
                AlembicSyncConfig,
                SyncSessionConfig, 
            )
            value = globals()[attr_name] = locals()[attr_name]

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.sync.{attr_name}",
            version="2.11",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated, please "
            f"import it from '{module}' instead",
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import (
        SQLAlchemySyncConfig,
        AlembicSyncConfig,
        SyncSessionConfig, 
    )
    from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
        default_before_send_handler,
        autocommit_before_send_handler,
    )
