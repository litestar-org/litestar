"""SQLAlchemy exception utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ("wrap_sqlalchemy_exception",)

if TYPE_CHECKING:
    from advanced_alchemy.exceptions import wrap_sqlalchemy_exception
else:
    from advanced_alchemy.exceptions import wrap_sqlalchemy_exception
