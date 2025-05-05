"""
Repository module for SQLAlchemy integration.

This module re-exports the repository classes from advanced_alchemy.repository
to enable direct imports from litestar.plugins.sqlalchemy.repository.
"""
# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
from __future__ import annotations

from advanced_alchemy.repository import (
    ModelT,
    SQLAlchemyAsyncRepository,
    SQLAlchemySyncRepository,
)

__all__ = (
    "ModelT",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemySyncRepository",
)