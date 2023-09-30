try:
    from advanced_alchemy.exceptions import ConflictError, NotFoundError, RepositoryError
except ImportError:
    from ._exceptions import ConflictError, NotFoundError, RepositoryError  # type: ignore[assignment]

__all__ = ("ConflictError", "NotFoundError", "RepositoryError")
