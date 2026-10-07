# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import Collection
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from typing import TYPE_CHECKING, Any

from msgspec import Raw, Struct
from msgspec.msgpack import Ext
from typing_extensions import TypeAliasType

if TYPE_CHECKING:
    from collections import deque
    from datetime import date, datetime, time
    from decimal import Decimal
    from enum import Enum, IntEnum
    from pathlib import Path, PurePath
    from re import Pattern
    from uuid import UUID

    from litestar.types import DataclassProtocol

    try:
        from attrs import AttrsInstance
    except ImportError:
        AttrsInstance = Any  # type: ignore[assignment, misc]

__all__ = (
    "DataContainerType",
    "EncodableBuiltinCollectionType",
    "EncodableBuiltinType",
    "EncodableMsgSpecType",
    "EncodableStdLibIPType",
    "EncodableStdLibType",
    "LitestarEncodableType",
)

EncodableBuiltinType = TypeAliasType("EncodableBuiltinType", None | bool | int | float | str | bytes | bytearray)
EncodableBuiltinCollectionType = TypeAliasType(
    "EncodableBuiltinCollectionType", list | tuple | set | frozenset | dict | Collection
)
EncodableStdLibType = TypeAliasType(
    "EncodableStdLibType",
    (
        "date | datetime | deque | time | UUID | Decimal | Enum | IntEnum | DataclassProtocol | Path | PurePath | Pattern"
    ),
)
EncodableStdLibIPType = TypeAliasType(
    "EncodableStdLibIPType", IPv4Address | IPv4Interface | IPv4Network | IPv6Address | IPv6Interface | IPv6Network
)
EncodableMsgSpecType = TypeAliasType("EncodableMsgSpecType", Ext | Raw | Struct)
LitestarEncodableType = TypeAliasType("LitestarEncodableType", Any)  # pyright: ignore # TODO: Remove this)
DataContainerType = TypeAliasType("DataContainerType", Any)  # pyright: ignore  # TODO: Remove this)
