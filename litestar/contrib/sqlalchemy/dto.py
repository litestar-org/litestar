"""SQLAlchemy DTO configuration."""

# ruff: noqa: TCH004
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("SQLAlchemyDTO", "SQLAlchemyDTOConfig")


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy' is deprecated, please "
            f"import it from 'litestar.plugins.sqlalchemy.dto' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.dto import (  # pyright: ignore[reportMissingImports]
        SQLAlchemyDTO,
        SQLAlchemyDTOConfig,
    )
