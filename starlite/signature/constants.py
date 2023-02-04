from datetime import date, datetime, time
from enum import EnumMeta
from typing import Any, NamedTuple
from uuid import UUID

from msgspec import Raw, Struct
from msgspec.inspect import (
    AnyType,
    BoolType,
    ByteArrayType,
    BytesType,
    DataclassType,
    DateTimeType,
    DateType,
    DictType,
    EnumType,
    ExtType,
    FloatType,
    IntType,
    NamedTupleType,
    NoneType,
    RawType,
    StrType,
    StructType,
    TimeType,
    TupleType,
    TypedDictType,
    UUIDType,
)
from msgspec.msgpack import Ext
from pydantic_factories.protocols import DataclassProtocol

from starlite.types.builtin_types import TypedDictClass

MSGSPEC_TYPE_MAPPING = {
    AnyType: Any,
    NoneType: None,
    BoolType: bool,
    IntType: int,
    FloatType: float,
    StrType: str,
    BytesType: bytes,
    ByteArrayType: bytearray,
    DateTimeType: datetime,
    TimeType: time,
    DateType: date,
    UUIDType: UUID,
    ExtType: Ext,
    RawType: Raw,
    EnumType: EnumMeta,
    TupleType: tuple,
    DictType: dict,
    TypedDictType: TypedDictClass,
    NamedTupleType: NamedTuple,
    DataclassType: DataclassProtocol,
    StructType: Struct,
}
