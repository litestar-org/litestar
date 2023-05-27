from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import Column, DateTime, Table, type_coerce, util
from sqlalchemy.dialects.oracle import BLOB as ORA_BLOB
from sqlalchemy.dialects.oracle import RAW as ORA_RAW
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import coercions, roles, visitors
from sqlalchemy.sql.base import _NONE_NAME
from sqlalchemy.sql.schema import _copy_expression
from sqlalchemy.types import BINARY, CHAR, BigInteger, Integer, SchemaType, TypeDecorator
from sqlalchemy.types import JSON as _JSON

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect
    from sqlalchemy.sql._typing import _InfoType, _TextCoercedExpressionArgument
    from sqlalchemy.sql.schema import _ConstraintNameArgument


class TZDateTime(TypeDecorator):
    """Platform-independent timezone to utc datetime object."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is not None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value


class BigIntIdentity(TypeDecorator):
    """Platform-independent BigInteger Primary Key.

    User a Big Integer on engines that support it.

    Uses Integer for sqlite since there is no

    """

    impl = BigInteger
    cache_ok = True
    python_type = int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Big Integer Identity type"""

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Integer())
        if dialect.name == "duckdb":
            return dialect.type_descriptor(Integer())
        return dialect.type_descriptor(BigInteger())


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, Oracle's RAW(16) type, otherwise uses
    BINARY(16) or CHAR(32), storing as stringified hex values.

    Will accept stringified UUIDs as a hexstring or an actual UUID

    """

    impl = BINARY(16)
    cache_ok = True
    python_type = uuid.UUID

    def __init__(self, *args: Any, binary: bool = True, **kwargs: Any) -> None:
        self.binary = binary

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        if dialect.name == "duckdb":
            return dialect.type_descriptor(PG_UUID())
        if dialect.name == "oracle":
            return dialect.type_descriptor(ORA_RAW(16))
        if self.binary:
            return dialect.type_descriptor(BINARY(16))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: bytes | str | uuid.UUID | None, dialect: Dialect) -> bytes | str | None:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        value = self.to_uuid(value)
        if value is None:
            return value
        if dialect.name == "oracle":
            return value.bytes
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


class OracleJSONConstraint(SchemaType):
    """A a constraint for a .

    Can be included in the definition of a Table or Column.
    """

    _allow_multiple_tables = True

    __visit_name__ = "json_column_constraint"

    def __init__(
        self,
        sqltext: _TextCoercedExpressionArgument[Any],
        name: _ConstraintNameArgument = None,
        deferrable: bool | None = None,
        initially: str | None = None,
        table: Table | None = None,
        info: _InfoType | None = None,
        _create_rule: Any | None = None,
        _autoattach: bool = True,
        _type_bound: bool = False,
        **dialect_kw: Any,
    ) -> None:
        self.sqltext = coercions.expect(roles.DDLExpressionRole, sqltext)
        columns: list[Column[Any]] = []
        visitors.traverse(self.sqltext, {}, {"column": columns.append})

        super().__init__(
            name=name,
            deferrable=deferrable,
            initially=initially,
            _create_rule=_create_rule,
            info=info,
            _type_bound=_type_bound,
            _autoattach=_autoattach,
            *columns,  # noqa: B026
            **dialect_kw,
        )
        if table is not None:
            self._set_parent_with_dispatch(table)

    @property
    def is_column_level(self) -> bool:
        return not isinstance(self.parent, Table)

    def _copy(self, *, target_table: Table | None = None, **kw: Any) -> OracleJSONConstraint:
        # note that target_table is None for the copy process of
        # a column-bound CheckConstraint, so this path is not reached
        # in that case.
        sqltext = _copy_expression(self.sqltext, self.table, target_table) if target_table is not None else self.sqltext

        c = OracleJSONConstraint(
            sqltext,
            name=self.name,
            initially=self.initially,
            deferrable=self.deferrable,
            _create_rule=self._create_rule,
            table=target_table,
            comment=self.comment,
            _autoattach=False,
            _type_bound=self._type_bound,
        )
        return self._schema_item_copy(c)


class JSON(TypeDecorator):
    """Platform-independent JSON type.

    Uses JSONB type for postgres, BLOB for Oracle, otherwise uses the generic JSON data type.

    JSON = _JSON().with_variant(PG_JSONB, "postgresql").with_variant(ORA_BLOB, "oracle")

    """

    impl = _JSON
    cache_ok = True
    python_type = dict

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize JSON type"""

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())  # type: ignore
        if dialect.name == "oracle":
            return dialect.type_descriptor(ORA_BLOB())
        return dialect.type_descriptor(_JSON())

    def _should_create_constraint(self, compiler: Any, **kw: Any) -> bool:
        if compiler.dialect.name == "oracle":
            return True
        return False

    @util.preload_module("sqlalchemy.sql.schema")
    def _set_table(self, column, table):
        schema = util.preloaded.sql_schema
        if not self.create_constraint:
            return

        variant_mapping = self._variant_mapping_for_set_table(column)

        _e = schema.CheckConstraint(
            type_coerce(column, self).in_([0, 1]),
            name=_NONE_NAME if self.name is None else self.name,
            _create_rule=util.portable_instancemethod(  # type: ignore
                self._should_create_constraint,
                {"variant_mapping": variant_mapping},
            ),
            _type_bound=True,
        )
