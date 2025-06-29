# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
"""SQLAlchemy exception utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ("wrap_sqlalchemy_exception",)

if TYPE_CHECKING:
    from advanced_alchemy.exceptions import (  # pyright: ignore[reportMissingImports]
        wrap_sqlalchemy_exception,
    )
else:
    from advanced_alchemy.exceptions import (  # pyright: ignore[reportMissingImports]
        wrap_sqlalchemy_exception,
    )
