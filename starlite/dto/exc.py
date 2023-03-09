from __future__ import annotations

from starlite.exceptions import StarliteException

__all__ = ("DTOException", "InvalidAnnotation")


class DTOException(StarliteException):
    """Base DTO exception type."""


class InvalidAnnotation(DTOException):
    """Unexpected DTO type argument."""
