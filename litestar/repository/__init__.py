from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AbstractAsyncRepository",
    "AbstractSyncRepository",
    "ConflictError",
    "FilterTypes",
    "NotFoundError",
    "RepositoryError",
)

_ALTERNATIVES = {
    "AbstractAsyncRepository": "advanced_alchemy.repository.SQLAlchemyAsyncRepository",
    "AbstractSyncRepository": "advanced_alchemy.repository.SQLAlchemySyncRepository",
    "ConflictError": "advanced_alchemy.exceptions.IntegrityError",
    "FilterTypes": "advanced_alchemy.filters.FilterTypes",
    "NotFoundError": "advanced_alchemy.exceptions.NotFoundError",
    "RepositoryError": "advanced_alchemy.exceptions.RepositoryError",
}


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name in ("AbstractAsyncRepository", "AbstractSyncRepository"):
            from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository

            value: object = (
                SQLAlchemyAsyncRepository if attr_name == "AbstractAsyncRepository" else SQLAlchemySyncRepository
            )
        elif attr_name in ("ConflictError", "NotFoundError", "RepositoryError"):
            try:
                from advanced_alchemy.exceptions import IntegrityError as ConflictError
                from advanced_alchemy.exceptions import NotFoundError, RepositoryError
            except ImportError:  # pragma: no cover
                from litestar.repository._exceptions import (  # type: ignore[assignment]
                    ConflictError,
                    NotFoundError,
                    RepositoryError,
                )

            value = {
                "ConflictError": ConflictError,
                "NotFoundError": NotFoundError,
                "RepositoryError": RepositoryError,
            }[attr_name]
        elif attr_name == "FilterTypes":
            try:
                from advanced_alchemy.filters import FilterTypes
            except ImportError:  # pragma: no cover
                from litestar.repository._filters import FilterTypes

            value = FilterTypes
        else:  # pragma: no cover
            raise RuntimeError(f"Unhandled module attribute: {attr_name!r}")

        warn_deprecation(
            deprecated_name=f"litestar.repository.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            alternative=_ALTERNATIVES[attr_name],
            info=f"importing {attr_name} from 'litestar.repository' is deprecated, please "
            f"import it from '{_ALTERNATIVES[attr_name]}' instead",
        )

        globals()[attr_name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.exceptions import IntegrityError as ConflictError
    from advanced_alchemy.exceptions import NotFoundError, RepositoryError
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.repository import (
        SQLAlchemyAsyncRepository as AbstractAsyncRepository,
    )
    from advanced_alchemy.repository import (
        SQLAlchemySyncRepository as AbstractSyncRepository,
    )
