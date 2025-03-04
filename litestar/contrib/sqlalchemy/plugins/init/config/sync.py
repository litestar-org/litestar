# ruff: noqa: TC004, F401

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AlembicSyncConfig",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
    "autocommit_before_send_handler",
    "default_before_send_handler",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name == "SQLAlchemySyncConfig":
            from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
                SQLAlchemySyncConfig as _SQLAlchemySyncConfig,
            )
            from sqlalchemy import Engine

            from litestar.contrib.sqlalchemy.plugins.init.config.compat import (
                _CreateEngineMixin,  # pyright: ignore[reportPrivateUsage]
            )

            class SQLAlchemySyncConfig(_SQLAlchemySyncConfig, _CreateEngineMixin[Engine]): ...

            module = "litestar.plugins.sqlalchemy"
            value = globals()[attr_name] = SQLAlchemySyncConfig
        elif attr_name in {"default_before_send_handler", "autocommit_before_send_handler"}:
            module = "litestar.plugins.sqlalchemy.plugins.init.config.sync"
            from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
                autocommit_before_send_handler,  # pyright: ignore[reportUnusedImport]
                default_before_send_handler,  # pyright: ignore[reportUnusedImport]
            )

            value = globals()[attr_name] = locals()[attr_name]
        else:
            module = "litestar.plugins.sqlalchemy"
            from advanced_alchemy.extensions.litestar import (
                AlembicSyncConfig,  # pyright: ignore[reportUnusedImport]
                SyncSessionConfig,  # pyright: ignore[reportUnusedImport]
            )

            value = globals()[attr_name] = locals()[attr_name]

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.sync.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated, please "
            f"import it from '{module}' instead",
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import (
        AlembicSyncConfig,
        SQLAlchemySyncConfig,
        SyncSessionConfig,
    )
    from advanced_alchemy.extensions.litestar.plugins.init.config.sync import (
        autocommit_before_send_handler,
        default_before_send_handler,
    )
