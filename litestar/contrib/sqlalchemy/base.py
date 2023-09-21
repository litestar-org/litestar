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
    touch_updated_timestamp,
)

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
