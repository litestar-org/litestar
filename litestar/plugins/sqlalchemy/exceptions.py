"""
Exceptions module for SQLAlchemy integration.

This module re-exports the exception wrapper from advanced_alchemy.exceptions
to enable direct imports from litestar.plugins.sqlalchemy.exceptions.
"""
# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
from __future__ import annotations

from advanced_alchemy.exceptions import wrap_sqlalchemy_exception

__all__ = ("wrap_sqlalchemy_exception",)
