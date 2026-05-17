from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AbstractAsyncRepository",
    "AbstractSyncRepository",
)

_ALTERNATIVES = {
    "AbstractAsyncRepository": "advanced_alchemy.repository.SQLAlchemyAsyncRepository",
    "AbstractSyncRepository": "advanced_alchemy.repository.SQLAlchemySyncRepository",
}


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository

        mapping = {
            "AbstractAsyncRepository": SQLAlchemyAsyncRepository,
            "AbstractSyncRepository": SQLAlchemySyncRepository,
        }

        warn_deprecation(
            deprecated_name=f"litestar.repository.abc.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            alternative=_ALTERNATIVES[attr_name],
            info=f"importing {attr_name} from 'litestar.repository.abc' is deprecated, please "
            f"import it from '{_ALTERNATIVES[attr_name]}' instead",
        )

        value = globals()[attr_name] = mapping[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from advanced_alchemy.repository import (
        SQLAlchemyAsyncRepository as AbstractAsyncRepository,
    )
    from advanced_alchemy.repository import (
        SQLAlchemySyncRepository as AbstractSyncRepository,
    )
