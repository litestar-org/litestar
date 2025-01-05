# ruff: noqa: TC004
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("SQLAlchemySerializationPlugin",)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.plugins.serialization.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.plugins.serialization' is deprecated, please "
            "import it from 'litestar.plugins.sqlalchemy' instead",
        )
        from advanced_alchemy.extensions.litestar import SQLAlchemySerializationPlugin

        value = globals()[attr_name] = SQLAlchemySerializationPlugin
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import SQLAlchemySerializationPlugin
