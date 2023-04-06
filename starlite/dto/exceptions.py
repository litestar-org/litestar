from __future__ import annotations

from starlite.exceptions import ImproperlyConfiguredException

__all__ = ["DTOException", "UnsupportedType"]


class DTOException(ImproperlyConfiguredException):
    """Base exception for DTO errors."""


class UnsupportedType(DTOException):
    """Raised when a type is not supported by Starlite."""
