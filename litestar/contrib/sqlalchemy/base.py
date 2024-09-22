"""Application ORM configuration."""

# ruff: noqa: TCH004, F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "AuditColumns",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntPrimaryKey",
    "CommonTableAttributes",
    "ModelProtocol",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDPrimaryKey",
    "create_registry",
    "orm_registry",
    "touch_updated_timestamp",
)


def __getattr__(attr_name: str) -> object:
    from advanced_alchemy import base  # pyright: ignore[reportMissingImports,reportUnusedImport]

    try:
        # v0.6.0+
        from advanced_alchemy._listeners import touch_updated_timestamp  # pyright: ignore
    except ImportError:
        from advanced_alchemy.base import touch_updated_timestamp  # type: ignore[no-redef,attr-defined]

    if attr_name in __all__:
        if attr_name == "touch_updated_timestamp":
            warn_deprecation(
                deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
                version="2.12",
                kind="import",
                removal_in="3.0",
                info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy' is deprecated, please"
                f"see the 'Advanced Alchemy' documentation for more details on how to use '{attr_name}' instead",
            )
            value = globals()[attr_name] = touch_updated_timestamp  # pyright: ignore[reportUnknownVariableType]
            return value  # pyright: ignore[reportUnknownVariableType]
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy' is deprecated, please"
            f"import it from 'litestar.plugins.sqlalchemy.base.{attr_name}' instead",
        )

        value = globals()[attr_name] = getattr(base, attr_name)
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    try:
        # v0.6.0+
        from advanced_alchemy._listeners import touch_updated_timestamp  # pyright: ignore
    except ImportError:
        from advanced_alchemy.base import touch_updated_timestamp  # type: ignore[no-redef,attr-defined]

    from advanced_alchemy.base import (  # pyright: ignore[reportMissingImports]
        AuditColumns,
        BigIntAuditBase,
        BigIntBase,
        BigIntPrimaryKey,
        CommonTableAttributes,
        ModelProtocol,
        UUIDAuditBase,
        UUIDBase,
        UUIDPrimaryKey,
        create_registry,
        orm_registry,
    )
