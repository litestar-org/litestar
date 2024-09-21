from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "SESSION_SCOPE_KEY",
    "SESSION_TERMINUS_ASGI_EVENTS",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
    "GenericAlembicConfig",
)

def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name in ("GenericSQLAlchemyConfig", "GenericSessionConfig", "GenericAlembicConfig"):
            from advanced_alchemy.config.common import GenericAlembicConfig, GenericSessionConfig, GenericSQLAlchemyConfig
            module = 'litestar.plugins.sqlalchemy.config'
        else:
            module = 'litestar.plugins.sqlalchemy.plugins.init.config.common'
            from advanced_alchemy.extensions.litestar.plugins.init.config.common import (
                SESSION_SCOPE_KEY,
                SESSION_TERMINUS_ASGI_EVENTS,
            )
        
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.common.{attr_name}",
            version="2.11",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated, please "
            f"import it from '{module}' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")

if TYPE_CHECKING:
    from advanced_alchemy.config.common import GenericAlembicConfig, GenericSessionConfig, GenericSQLAlchemyConfig
    from advanced_alchemy.extensions.litestar.plugins.init.config.common import (
        SESSION_SCOPE_KEY,
        SESSION_TERMINUS_ASGI_EVENTS,
    )
