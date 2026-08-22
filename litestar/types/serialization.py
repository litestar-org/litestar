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
from typing import TYPE_CHECKING, Any, TypeAlias

from msgspec import Raw, Struct
from msgspec.msgpack import Ext

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

EncodableBuiltinType: TypeAlias = None | bool | int | float | str | bytes | bytearray
EncodableBuiltinCollectionType: TypeAlias = list | tuple | set | frozenset | dict | Collection
EncodableStdLibType: TypeAlias = (
    "date | datetime | deque | time | UUID | Decimal | Enum | IntEnum | DataclassProtocol | Path | PurePath | Pattern"
)
EncodableStdLibIPType: TypeAlias = IPv4Address | IPv4Interface | IPv4Network | IPv6Address | IPv6Interface | IPv6Network
EncodableMsgSpecType: TypeAlias = Ext | Raw | Struct
LitestarEncodableType: TypeAlias = Any  # pyright: ignore # TODO: Remove this
DataContainerType: TypeAlias = Any  # pyright: ignore  # TODO: Remove this
