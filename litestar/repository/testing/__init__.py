from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("GenericAsyncMockRepository", "GenericSyncMockRepository")


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
            info=f"importing {attr_name} from 'litestar.repository.testing' is deprecated. There is "
            f"no direct replacement; rewrite tests against a real repository or use the testing "
            f"utilities provided by 'advanced_alchemy'.",
        )

        value = globals()[attr_name] = mapping[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.repository.testing.generic_mock_repository import (
        GenericAsyncMockRepository,
        GenericSyncMockRepository,
    )
