"""SQLAlchemy base utilities."""
from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from advanced_alchemy._listeners import touch_updated_timestamp
    from advanced_alchemy.base import (
        BigIntAuditBase,
        BigIntBase,
        CommonTableAttributes,
        ModelProtocol,
        UUIDAuditBase,
        UUIDBase,
        create_registry,
        orm_registry,
    )
    from advanced_alchemy.mixins import (
        AuditColumns,
        BigIntPrimaryKey,
        UUIDPrimaryKey,
    )
else:
    from advanced_alchemy._listeners import touch_updated_timestamp
    from advanced_alchemy.base import (
        BigIntAuditBase,
        BigIntBase,
        CommonTableAttributes,
        ModelProtocol,
        UUIDAuditBase,
        UUIDBase,
        create_registry,
        orm_registry,
    )
    from advanced_alchemy.mixins import (
        AuditColumns,
        BigIntPrimaryKey,
        UUIDPrimaryKey,
    )
