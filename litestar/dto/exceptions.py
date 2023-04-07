from __future__ import annotations

from litestar.exceptions import ImproperlyConfiguredException

__all__ = ["DTOException", "UnsupportedType"]


class DTOException(ImproperlyConfiguredException):
    """Base exception for DTO errors."""


class UnsupportedType(DTOException):
    """Raised when a type is not supported by Litestar."""
