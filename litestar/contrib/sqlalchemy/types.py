from __future__ import annotations

import datetime
import uuid
from base64 import b64decode
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import DateTime, text, util
from sqlalchemy.dialects.oracle import BLOB as ORA_BLOB
from sqlalchemy.dialects.oracle import RAW as ORA_RAW
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import BINARY, CHAR, BigInteger, Integer, SchemaType, TypeDecorator, TypeEngine
from sqlalchemy.types import JSON as _JSON

from litestar.serialization import decode_json, encode_json

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, Oracle's RAW(16) type, otherwise uses
    BINARY(16) or CHAR(32), storing as stringified hex values.

    Will accept stringified UUIDs as a hexstring or an actual UUID

    """

    impl = BINARY(16)
    cache_ok = True

    @property
    def python_type(self) -> type[uuid.UUID]:
        return uuid.UUID

    def __init__(self, *args: Any, binary: bool = True, **kwargs: Any) -> None:
        self.binary = binary

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name in {"postgresql", "duckdb"}:
            return dialect.type_descriptor(PG_UUID())
        if dialect.name == "oracle":
            return dialect.type_descriptor(ORA_RAW(16))
        if self.binary:
            return dialect.type_descriptor(BINARY(16))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: bytes | str | uuid.UUID | None, dialect: Dialect) -> bytes | str | None:
        if value is None:
            return value
        if dialect.name in {"postgresql", "duckdb"}:
            return str(value)
        value = self.to_uuid(value)
        if value is None:
            return value
        if dialect.name in {"oracle", "spanner+spanner"}:
            return value.bytes
        return value.bytes if self.binary else value.hex

    def process_result_value(self, value: bytes | str | uuid.UUID | None, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        if dialect.name == "spanner+spanner":
            return uuid.UUID(bytes=b64decode(value))
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


class ORA_JSONB(TypeDecorator, SchemaType):  # type: ignore  # noqa: N801
    """Oracle Binary JSON type.

    JsonB = _JSON().with_variant(PG_JSONB, "postgresql").with_variant(ORA_JSONB, "oracle")

    """

    impl = ORA_BLOB
    cache_ok = True

    @property
    def python_type(self) -> type[dict[str, Any]]:
        return dict

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize JSON type"""
        self.name = kwargs.pop("name", None)
        self.oracle_strict = kwargs.pop("oracle_strict", True)

    def coerce_compared_value(self, op: Any, value: Any) -> Any:
        return self.impl.coerce_compared_value(op=op, value=value)  # type: ignore

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        return dialect.type_descriptor(ORA_BLOB())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any | None:
        return value if value is None else encode_json(value)

    def process_result_value(self, value: bytes | None, dialect: Dialect) -> Any | None:
        return value if value is None else decode_json(value=value)

    def _should_create_constraint(self, compiler: Any, **kw: Any) -> bool:
        return cast("bool", compiler.dialect.name == "oracle")

    def _variant_mapping_for_set_table(self, column: Any) -> dict | None:
        if column.type._variant_mapping:
            variant_mapping = dict(column.type._variant_mapping)
            variant_mapping["_default"] = column.type
        else:
            variant_mapping = None
        return variant_mapping

    @util.preload_module("sqlalchemy.sql.schema")
    def _set_table(self, column: Any, table: Any) -> None:
        schema = util.preloaded.sql_schema
        variant_mapping = self._variant_mapping_for_set_table(column)
        constraint_options = "(strict)" if self.oracle_strict else ""
        sqltext = text(f"{column.name} is json {constraint_options}")
        e = schema.CheckConstraint(
            sqltext,
            name=f"{column.name}_is_json",
            _create_rule=util.portable_instancemethod(  # type: ignore[no-untyped-call]
                self._should_create_constraint,
                {"variant_mapping": variant_mapping},
            ),
            _type_bound=True,
        )
        table.append_constraint(e)


class DateTimeUTC(TypeDecorator):
    """Timezone Aware DateTime.

    Ensure UTC is stored in the database and that TZ aware dates are returned for all dialects.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is None:
            return value
        if not value.tzinfo:
            raise TypeError("tzinfo is required")
        return value.astimezone(datetime.timezone.utc)

    def process_result_value(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value


BigIntIdentity = BigInteger().with_variant(Integer, "sqlite")
"""A ``BigInteger`` variant that reverts to an ``Integer`` for unsupported variants."""

JsonB = _JSON().with_variant(PG_JSONB, "postgresql").with_variant(ORA_JSONB, "oracle")
"""A JSON type that uses  native ``JSONB`` where possible and ``Binary`` or ``Blob`` as
an alternative.
"""
