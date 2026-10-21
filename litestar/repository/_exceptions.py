from __future__ import annotations

__all__ = ("ConflictError", "NotFoundError", "RepositoryError")


class RepositoryError(Exception):
    """Base repository exception type."""


class ConflictError(RepositoryError):
    """Data integrity error."""


class NotFoundError(RepositoryError):
    """An identity does not exist."""
