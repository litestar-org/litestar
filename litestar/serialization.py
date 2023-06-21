from __future__ import annotations

from collections import deque
from datetime import date, datetime, time
from decimal import Decimal
from functools import partial
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import Path, PurePath
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar, cast, overload
from uuid import UUID

import msgspec
from msgspec import ValidationError

from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.types import Empty, Serializer
from litestar.utils import is_class_and_subclass, is_pydantic_model_class

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from litestar.types import TypeEncodersMap

__all__ = (
    "dec_hook",
    "decode_json",
    "decode_media_type",
    "decode_msgpack",
    "default_serializer",
    "encode_json",
    "encode_msgpack",
    "get_serializer",
)

T = TypeVar("T")


PYDANTIC_DECODERS: list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]] = []

try:
    import pydantic

    PYDANTIC_ENCODERS: dict[Any, Callable[[Any], Any]] = {
        pydantic.EmailStr: str,
        pydantic.NameEmail: str,
        pydantic.ByteSize: lambda val: val.real,
    }

    def _dec_pydantic(type_: type[pydantic.BaseModel], value: Any) -> pydantic.BaseModel:
        return type_.model_validate(value, strict=False) if hasattr(type_, "model_validate") else type_.parse_obj(value)

    PYDANTIC_DECODERS.append((is_pydantic_model_class, _dec_pydantic))

    if pydantic.VERSION.startswith("1"):  # pragma: no cover
        PYDANTIC_ENCODERS.update(
            {
                pydantic.BaseModel: lambda model: model.dict(),
                pydantic.SecretField: str,
                pydantic.StrictBool: int,
                pydantic.color.Color: str,  # pyright: ignore
                pydantic.ConstrainedBytes: lambda val: val.decode("utf-8"),
                pydantic.ConstrainedDate: lambda val: val.isoformat(),
            }
        )

        PydanticUUIDType: TypeAlias = (
            "type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5]"
        )

        def _dec_pydantic_uuid(type_: PydanticUUIDType, val: Any) -> PydanticUUIDType:
            if isinstance(val, str):
                val = type_(val)

            elif isinstance(val, (bytes, bytearray)):
                try:
                    val = type_(val.decode())
                except ValueError:
                    # 16 bytes in big-endian order as the bytes argument fail
                    # the above check
                    val = type_(bytes=val)
            elif isinstance(val, UUID):
                val = type_(str(val))

            if not isinstance(val, type_):
                raise ValidationError(f"Invalid UUID: {val!r}")

            if type_._required_version != val.version:  # type: ignore
                raise ValidationError(f"Invalid UUID version: {val!r}")

            return cast("PydanticUUIDType", val)

        def _is_pydantic_uuid(value: Any) -> bool:
            return is_class_and_subclass(value, (pydantic.UUID1, pydantic.UUID3, pydantic.UUID4, pydantic.UUID5))

        PYDANTIC_DECODERS.append((_is_pydantic_uuid, _dec_pydantic_uuid))
    else:
        from pydantic_extra_types import color

        PYDANTIC_ENCODERS.update(
            {
                pydantic.BaseModel: lambda model: model.model_dump(mode="json"),
                color.Color: str,
                pydantic.types.SecretStr: lambda val: "**********" if val else "",
                pydantic.types.SecretBytes: lambda val: "**********" if val else "",
            }
        )


except ImportError:
    PYDANTIC_ENCODERS = {}


DEFAULT_TYPE_ENCODERS: TypeEncodersMap = {
    Path: str,
    PurePath: str,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    datetime: lambda val: val.isoformat(),
    date: lambda val: val.isoformat(),
    time: lambda val: val.isoformat(),
    deque: list,
    Decimal: lambda val: int(val) if val.as_tuple().exponent >= 0 else float(val),
    Pattern: lambda val: val.pattern,
    # support subclasses of stdlib types, If no previous type matched, these will be
    # the last type in the mro, so we use this to (attempt to) convert a subclass into
    # its base class. # see https://github.com/jcrist/msgspec/issues/248
    # and https://github.com/litestar-org/litestar/issues/1003
    str: str,
    int: int,
    float: float,
    set: set,
    frozenset: frozenset,
    bytes: bytes,
    **PYDANTIC_ENCODERS,
}


def default_serializer(value: Any, type_encoders: Mapping[Any, Callable[[Any], Any]] | None = None) -> Any:
    """Transform values non-natively supported by ``msgspec``

    Args:
        value: A value to serialized
        type_encoders: Mapping of types to callables to transforming types
    Returns:
        A serialized value
    Raises:
        TypeError: if value is not supported
    """
    if type_encoders is None:
        type_encoders = DEFAULT_TYPE_ENCODERS

    for base in value.__class__.__mro__[:-1]:
        try:
            encoder = type_encoders[base]
            return encoder(value)
        except KeyError:
            continue

    raise TypeError(f"Unsupported type: {type(value)!r}")


def dec_hook(type_: Any, value: Any) -> Any:  # pragma: no cover
    """Transform values non-natively supported by ``msgspec``

    Args:
        type_: Encountered type
        value: Value to coerce

    Returns:
        A ``msgspec``-supported type
    """

    from litestar.datastructures.state import ImmutableState

    if isinstance(value, type_):
        return value

    for predicate, decoder in PYDANTIC_DECODERS:
        if predicate(type_):
            return decoder(type_, value)

    if issubclass(type_, (Path, PurePath, ImmutableState, UUID)):
        return type_(value)

    raise TypeError(f"Unsupported type: {type(value)!r}")


_msgspec_json_encoder = msgspec.json.Encoder(enc_hook=default_serializer)
_msgspec_json_decoder = msgspec.json.Decoder(dec_hook=dec_hook)
_msgspec_msgpack_encoder = msgspec.msgpack.Encoder(enc_hook=default_serializer)
_msgspec_msgpack_decoder = msgspec.msgpack.Decoder(dec_hook=dec_hook)


def encode_json(obj: Any, default: Callable[[Any], Any] | None = None) -> bytes:
    """Encode a value into JSON.

    Args:
        obj: Value to encode
        default: Optional callable to support non-natively supported types.

    Returns:
        JSON as bytes

    Raises:
        SerializationException: If error encoding ``obj``.
    """
    try:
        return msgspec.json.encode(obj, enc_hook=default) if default else _msgspec_json_encoder.encode(obj)
    except (TypeError, msgspec.EncodeError) as msgspec_error:
        raise SerializationException(str(msgspec_error)) from msgspec_error


@overload
def decode_json(raw: str | bytes) -> Any:
    ...


@overload
def decode_json(raw: str | bytes, type_: type[T]) -> T:
    ...


def decode_json(raw: str | bytes, type_: Any = Empty) -> Any:
    """Decode a JSON string/bytes into an object.

    Args:
        raw: Value to decode
        type_: An optional type to decode the data into

    Returns:
        An object

    Raises:
        SerializationException: If error decoding ``raw``.
    """
    try:
        if type_ is Empty:
            return _msgspec_json_decoder.decode(raw)
        return msgspec.json.decode(raw, dec_hook=dec_hook, type=type_)
    except msgspec.DecodeError as msgspec_error:
        raise SerializationException(str(msgspec_error)) from msgspec_error


def encode_msgpack(obj: Any, enc_hook: Callable[[Any], Any] | None = default_serializer) -> bytes:
    """Encode a value into MessagePack.

    Args:
        obj: Value to encode
        enc_hook: Optional callable to support non-natively supported types

    Returns:
        MessagePack as bytes

    Raises:
        SerializationException: If error encoding ``obj``.
    """
    try:
        if enc_hook is None or enc_hook is default_serializer:
            return _msgspec_msgpack_encoder.encode(obj)
        return msgspec.msgpack.encode(obj, enc_hook=enc_hook)
    except (TypeError, msgspec.EncodeError) as msgspec_error:
        raise SerializationException(str(msgspec_error)) from msgspec_error


@overload
def decode_msgpack(raw: bytes) -> Any:
    ...


@overload
def decode_msgpack(raw: bytes, type_: type[T]) -> T:
    ...


def decode_msgpack(raw: bytes, type_: Any = Empty) -> Any:
    """Decode a MessagePack string/bytes into an object.

    Args:
        raw: Value to decode
        type_: An optional type to decode the data into

    Returns:
        An object

    Raises:
        SerializationException: If error decoding ``raw``.
    """
    try:
        if type_ is Empty:
            return _msgspec_msgpack_decoder.decode(raw)
        return msgspec.msgpack.decode(raw, dec_hook=dec_hook, type=type_)
    except msgspec.DecodeError as msgspec_error:
        raise SerializationException(str(msgspec_error)) from msgspec_error


def decode_media_type(raw: bytes, media_type: MediaType | str, type_: Any) -> Any:
    """Decode a raw value into an object.

    Args:
        raw: Value to decode
        media_type: Media type of the value
        type_: An optional type to decode the data into

    Returns:
        An object

    Raises:
        SerializationException: If error decoding ``raw`` or ``media_type`` unsupported.
    """
    if media_type == MediaType.JSON:
        return decode_json(raw, type_=type_)

    if media_type == MediaType.MESSAGEPACK:
        return decode_msgpack(raw, type_=type_)

    raise SerializationException(f"Unsupported media type: '{media_type}'")


def get_serializer(type_encoders: TypeEncodersMap | None = None) -> Serializer:
    """Get the serializer for the given type encoders."""

    if type_encoders:
        return partial(default_serializer, type_encoders={**DEFAULT_TYPE_ENCODERS, **type_encoders})

    return default_serializer
