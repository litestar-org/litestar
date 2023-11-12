try:
    from advanced_alchemy.exceptions import ConflictError, NotFoundError, RepositoryError
except ImportError:  # pragma: no cover
    from ._exceptions import ConflictError, NotFoundError, RepositoryError  # type: ignore[assignment]

__all__ = ("ConflictError", "NotFoundError", "RepositoryError")
