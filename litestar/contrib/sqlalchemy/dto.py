# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
"""SQLAlchemy DTO configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("SQLAlchemyDTO", "SQLAlchemyDTOConfig")


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from advanced_alchemy.extensions.litestar.dto import (
            SQLAlchemyDTO,  # pyright: ignore[reportMissingImports]
            SQLAlchemyDTOConfig,  # pyright: ignore[reportMissingImports]
        )

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.dto' is deprecated, please "
            f"import it from 'litestar.plugins.sqlalchemy.dto' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.dto import (
        SQLAlchemyDTO,  # pyright: ignore[reportMissingImports]
        SQLAlchemyDTOConfig,  # pyright: ignore[reportMissingImports]
    )
