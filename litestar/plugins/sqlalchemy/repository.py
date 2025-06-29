"""SQLAlchemy repository utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = (
    "ModelT",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemySyncRepository",
)

if TYPE_CHECKING:
    from advanced_alchemy.repository import (
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
else:
    from advanced_alchemy.repository import (
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
