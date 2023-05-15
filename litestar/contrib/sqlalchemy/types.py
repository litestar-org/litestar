from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import BINARY, CHAR, BigInteger, Integer, TypeDecorator
from sqlalchemy.types import JSON as _JSON

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect

BigIntIdentity = BigInteger().with_variant(Integer, "sqlite")
"""Platform-independent BigInteger Primary Key.

User a Big Integer on engines that support it.

Uses Integer for sqlite since there is no

"""


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    BINARY(16) or CHAR(32), storing as stringified hex values.

    Will accept stringified UUIDs as a hexstring or an actual UUID

    """

    impl = BINARY(16)
    cache_ok = True
    python_type = type(uuid.UUID)

    def __init__(self, length: int | None = None, binary: bool = True) -> None:
        self.length = length
        self.binary = binary
        if self.binary and self.length is None:
            self.length = 16
        elif not self.binary and self.length is None:
            self.length = 32

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        if self.binary:
            return dialect.type_descriptor(BINARY(length=self.length))
        return dialect.type_descriptor(CHAR(length=self.length))

    def process_bind_param(self, value: bytes | str | uuid.UUID | None, dialect: Dialect) -> bytes | str | None:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        value = self.to_uuid(value)
        if value is None:
            return value
        return value.bytes if self.binary else value.hex

    def process_result_value(self, value: bytes | str | uuid.UUID | None, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        if self.binary:
            return uuid.UUID(bytes=cast("bytes", value))
        return uuid.UUID(hex=cast("str", value))

    @staticmethod
    def to_uuid(value: Any) -> uuid.UUID | None:
        if isinstance(value, uuid.UUID) or value is None:
            return value
        try:
            value = uuid.UUID(hex=value)
        except (TypeError, ValueError):
            value = uuid.UUID(bytes=value)
        return cast("uuid.UUID | None", value)


JSON = _JSON().with_variant(PG_JSONB, "postgresql")
"""Platform-independent JSON type.

    Uses JSONB type for postgres, otherwise uses the generic JSON data type.
"""
