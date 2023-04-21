from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator
from sqlalchemy.types import JSON as _JSON

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Will accept stringified UUIDs as a hexstring or an actual UUID

    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: str | uuid.UUID | None, dialect: Dialect) -> str | None:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)

        if not isinstance(value, uuid.UUID):
            return "%.32x" % uuid.UUID(value).int

        # hexstring
        return "%.32x" % value.int

    def process_result_value(self, value: str | uuid.UUID | None, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class JSON(_JSON):
    """Platform-independent JSON type.

    Uses JSONB type for postgres, otherwise uses the generic JSON data type.
    """

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())  # type: ignore[no-untyped-call]
        return dialect.type_descriptor(_JSON())
