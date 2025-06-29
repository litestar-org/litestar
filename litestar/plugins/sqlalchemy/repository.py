# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
"""SQLAlchemy repository utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = (
    "ModelT",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemySyncRepository",
)

if TYPE_CHECKING:
    from advanced_alchemy.repository import (  # pyright: ignore[reportMissingImports]
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
else:
    from advanced_alchemy.repository import (  # pyright: ignore[reportMissingImports]
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
