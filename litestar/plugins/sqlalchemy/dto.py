"""SQLAlchemy DTO utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ("SQLAlchemyDTO", "SQLAlchemyDTOConfig")

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.dto import (
        SQLAlchemyDTO,
        SQLAlchemyDTOConfig,
    )
else:
    from advanced_alchemy.extensions.litestar.dto import (
        SQLAlchemyDTO,
        SQLAlchemyDTOConfig,
    )
