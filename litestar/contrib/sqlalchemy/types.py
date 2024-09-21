from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "GUID",
    "ORA_JSONB",
    "DateTimeUTC",
    "BigIntIdentity",
    "JsonB",
)

def __getattr__(attr_name: str) -> object:
    from advanced_alchemy.extensions.litestar.types import GUID, ORA_JSONB, BigIntIdentity, DateTimeUTC, JsonB # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]

    if attr_name in __all__:
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
            version="2.11",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy' is deprecated, please "
            f"import it from 'advanced_alchemy.extensions.litestar.types' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar.types import GUID, ORA_JSONB, BigIntIdentity, DateTimeUTC, JsonB # pyright: ignore[reportMissingImports]
