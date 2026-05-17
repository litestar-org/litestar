from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("GenericAsyncMockRepository", "GenericSyncMockRepository")

_ALTERNATIVES = {
    "GenericAsyncMockRepository": "advanced_alchemy.repository.memory.SQLAlchemyAsyncMockRepository",
    "GenericSyncMockRepository": "advanced_alchemy.repository.memory.SQLAlchemySyncMockRepository",
}


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.repository.testing.generic_mock_repository import (
            GenericAsyncMockRepository,
            GenericSyncMockRepository,
        )

        mapping = {
            "GenericAsyncMockRepository": GenericAsyncMockRepository,
            "GenericSyncMockRepository": GenericSyncMockRepository,
        }

        warn_deprecation(
            deprecated_name=f"litestar.repository.testing.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            alternative=_ALTERNATIVES[attr_name],
            info=f"importing {attr_name} from 'litestar.repository.testing' is deprecated, please "
            f"import it from '{_ALTERNATIVES[attr_name]}' instead",
        )

        value = globals()[attr_name] = mapping[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.repository.testing.generic_mock_repository import (
        GenericAsyncMockRepository,
        GenericSyncMockRepository,
    )
