"""Application ORM configuration."""
from __future__ import annotations


from advanced_alchemy.base import (
    AuditColumns,
    BigIntAuditBase,
    BigIntBase,
    BigIntPrimaryKey,
    CommonTableAttributes,
    ModelProtocol,
    create_registry,
    touch_updated_timestamp,
    UUIDAuditBase,
    UUIDBase,
    UUIDPrimaryKey,
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
)
