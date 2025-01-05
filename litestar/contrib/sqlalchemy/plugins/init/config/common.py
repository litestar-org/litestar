# ruff: noqa: TC004, F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "SESSION_SCOPE_KEY",
    "SESSION_TERMINUS_ASGI_EVENTS",
    "GenericAlembicConfig",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name in ("GenericSQLAlchemyConfig", "GenericSessionConfig", "GenericAlembicConfig"):
            module = "litestar.plugins.sqlalchemy.config"
            from advanced_alchemy.config.common import (  # pyright: ignore[reportMissingImports]
                GenericAlembicConfig,  # pyright: ignore[reportUnusedImport]
                GenericSessionConfig,  # pyright: ignore[reportUnusedImport]
                GenericSQLAlchemyConfig,  # pyright: ignore[reportUnusedImport]
            )
        else:
            from advanced_alchemy.extensions.litestar.plugins.init.config.common import (  # pyright: ignore[reportMissingImports]
                SESSION_SCOPE_KEY,  # pyright: ignore[reportUnusedImport]
                SESSION_TERMINUS_ASGI_EVENTS,  # pyright: ignore[reportUnusedImport]
            )

            module = "litestar.plugins.sqlalchemy.plugins.init.config.common"

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.common.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated, please "
            f"import it from '{module}' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.config.common import GenericAlembicConfig, GenericSessionConfig, GenericSQLAlchemyConfig
    from advanced_alchemy.extensions.litestar.plugins.init.config.common import (
        SESSION_SCOPE_KEY,
        SESSION_TERMINUS_ASGI_EVENTS,
    )
