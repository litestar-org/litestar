from __future__ import annotations

from litestar.exceptions import LitestarException

__all__ = ("DTOFactoryException", "InvalidAnnotation")


class DTOFactoryException(LitestarException):
    """Base DTO exception type."""


class InvalidAnnotation(DTOFactoryException):
    """Unexpected DTO type argument."""
