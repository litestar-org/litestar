from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("EngineConfig",)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from advanced_alchemy.extensions.litestar import EngineConfig

        module = "litestar.plugins.sqlalchemy"

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.init.config.engine.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.init.config.engine' is deprecated, please "
            f"import it from '{module}' instead",
        )
        value = globals()[attr_name] = EngineConfig
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import EngineConfig
