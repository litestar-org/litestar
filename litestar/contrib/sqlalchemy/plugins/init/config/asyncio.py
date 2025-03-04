# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AlembicAsyncConfig",
    "AsyncSessionConfig",
    "SQLAlchemyAsyncConfig",
    "autocommit_before_send_handler",
    "default_before_send_handler",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name == "SQLAlchemyAsyncConfig":
            from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
                SQLAlchemyAsyncConfig as _SQLAlchemyAsyncConfig,
            )
            from sqlalchemy.ext.asyncio import AsyncEngine

            from litestar.contrib.sqlalchemy.plugins.init.config.compat import (
                _CreateEngineMixin,  # pyright: ignore[reportPrivateUsage]
            )

            class SQLAlchemyAsyncConfig(_SQLAlchemyAsyncConfig, _CreateEngineMixin[AsyncEngine]): ...

            module = "litestar.plugins.sqlalchemy"
            value = globals()[attr_name] = SQLAlchemyAsyncConfig
        elif attr_name in {"default_before_send_handler", "autocommit_before_send_handler"}:
            module = "litestar.plugins.sqlalchemy.plugins.init.config.asyncio"
            from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
                autocommit_before_send_handler,
                default_before_send_handler,
            )

            value = globals()[attr_name] = locals()[attr_name]
        else:
            module = "litestar.plugins.sqlalchemy"
            from advanced_alchemy.extensions.litestar import (
                AlembicAsyncConfig,
                AsyncSessionConfig,
            )

            value = globals()[attr_name] = locals()[attr_name]

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.asyncio.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated, please "
            f"import it from '{module}' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import (
        AlembicAsyncConfig,
        AsyncSessionConfig,
        SQLAlchemyAsyncConfig,
    )
    from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
        autocommit_before_send_handler,
        default_before_send_handler,
    )
