# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
"""SQLAlchemy DTO utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ("SQLAlchemyDTO", "SQLAlchemyDTOConfig")

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.dto import (
        SQLAlchemyDTO,  # pyright: ignore[reportMissingImports]
        SQLAlchemyDTOConfig,  # pyright: ignore[reportMissingImports]
    )
else:
    from advanced_alchemy.extensions.litestar.dto import (
        SQLAlchemyDTO,  # pyright: ignore[reportMissingImports]
        SQLAlchemyDTOConfig,  # pyright: ignore[reportMissingImports]
    )
