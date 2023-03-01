from __future__ import annotations


class RepositoryError(Exception):
    """Base repository exception type."""


class ConflictError(RepositoryError):
    """Data integrity error."""


class NotFoundError(RepositoryError):
    """An identity does not exist."""
