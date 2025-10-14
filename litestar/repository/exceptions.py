try:
    from advanced_alchemy.exceptions import IntegrityError as ConflictError
    from advanced_alchemy.exceptions import NotFoundError, RepositoryError
except ImportError:  # pragma: no cover
    from litestar.repository._exceptions import (  # type: ignore[assignment]
        ConflictError,
        NotFoundError,
        RepositoryError,
    )

__all__ = ("ConflictError", "NotFoundError", "RepositoryError")
