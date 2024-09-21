from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "SQLAlchemyAsyncConfig",
    "AlembicAsyncConfig",
    "AsyncSessionConfig",
    "default_before_send_handler",
    "autocommit_before_send_handler",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name == "SQLAlchemyAsyncConfig":
            from litestar.contrib.sqlalchemy.plugins.init.config.compat import _CreateEngineMixin
            from sqlalchemy.ext.asyncio import AsyncEngine
            from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
                SQLAlchemyAsyncConfig as _SQLAlchemyAsyncConfig,
            )

            class SQLAlchemyAsyncConfig(_SQLAlchemyAsyncConfig, _CreateEngineMixin[AsyncEngine]): ...

            module = "litestar.plugins.sqlalchemy"
            value = globals()[attr_name] = SQLAlchemyAsyncConfig
        elif attr_name in {"default_before_send_handler", "autocommit_before_send_handler"}:
            module = "litestar.plugins.sqlalchemy.plugins.init.config.asyncio"
            from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
                default_before_send_handler,
                autocommit_before_send_handler,
            )

            value = globals()[attr_name] = locals()[attr_name]
        else:
            module = "litestar.plugins.sqlalchemy"
            from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
                AlembicAsyncConfig,
                AsyncSessionConfig,
            )

            value = globals()[attr_name] = autocommit_before_send_handler

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.asyncio.{attr_name}",
            version="2.11",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated, please "
            f"import it from '{module}' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine
    from litestar.contrib.sqlalchemy.plugins.init.config.compat import _CreateEngineMixin
    from advanced_alchemy.extensions.litestar import (
        SQLAlchemyAsyncConfig,
        AlembicAsyncConfig,
        AsyncSessionConfig, 
    )
    from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import (
        default_before_send_handler,
        autocommit_before_send_handler,
    )
