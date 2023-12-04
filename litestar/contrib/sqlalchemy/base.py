"""Application ORM configuration."""
from __future__ import annotations

from advanced_alchemy.base import (
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

try :
    # v0.6.0+
    from advanced_alchemy._listeners import touch_updated_timestamp
except ImportError:
    from advanced_alchemy.base import touch_updated_timestamp


__all__ = (
    "AuditColumns",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntPrimaryKey",
    "CommonTableAttributes",
    "create_registry",
    "ModelProtocol",
    "touch_updated_timestamp",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDPrimaryKey",
    "orm_registry",
)
