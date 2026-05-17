from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("ConflictError", "NotFoundError", "RepositoryError")

_ALTERNATIVES = {
    "ConflictError": "advanced_alchemy.exceptions.IntegrityError",
    "NotFoundError": "advanced_alchemy.exceptions.NotFoundError",
    "RepositoryError": "advanced_alchemy.exceptions.RepositoryError",
}


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        try:
            from advanced_alchemy.exceptions import IntegrityError as ConflictError
            from advanced_alchemy.exceptions import NotFoundError, RepositoryError
        except ImportError:  # pragma: no cover
            from litestar.repository._exceptions import (  # type: ignore[assignment]
                ConflictError,
                NotFoundError,
                RepositoryError,
            )

        mapping = {
            "ConflictError": ConflictError,
            "NotFoundError": NotFoundError,
            "RepositoryError": RepositoryError,
        }

        warn_deprecation(
            deprecated_name=f"litestar.repository.exceptions.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            alternative=_ALTERNATIVES[attr_name],
            info=f"importing {attr_name} from 'litestar.repository.exceptions' is deprecated, please "
            f"import it from '{_ALTERNATIVES[attr_name]}' instead",
        )

        value = globals()[attr_name] = mapping[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.exceptions import IntegrityError as ConflictError
    from advanced_alchemy.exceptions import NotFoundError, RepositoryError
