from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Union

import msgspec
from pydantic import (
    AnyUrl,
    BaseModel,
    ByteSize,
    ConstrainedBytes,
    ConstrainedDate,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedFrozenSet,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
    EmailStr,
    NameEmail,
    PaymentCardNumber,
    SecretField,
    StrictBool,
)
from pydantic.color import Color

if TYPE_CHECKING:
    from starlite.types import TypeEncodersMap

DEFAULT_TYPE_ENCODERS: "TypeEncodersMap" = {
    PurePosixPath: str,
    # pydantic specific types
    BaseModel: lambda m: m.dict(),
    ByteSize: lambda b: b.real,
    EmailStr: str,
    NameEmail: str,
    Color: str,
    AnyUrl: str,
    SecretField: str,
    ConstrainedInt: int,
    ConstrainedFloat: float,
    ConstrainedStr: str,
    ConstrainedBytes: lambda b: b.decode("utf-8"),
    ConstrainedList: list,
    ConstrainedSet: set,
    ConstrainedFrozenSet: frozenset,
    ConstrainedDecimal: float,
    ConstrainedDate: lambda d: d.isoformat(),
    PaymentCardNumber: str,
    StrictBool: int,  # pydantic compatibility
}


def default_serializer(value: Any, type_encoders: Optional[Dict[Any, Callable[[Any], Any]]] = None) -> Any:
    """Transform values non-natively supported by `msgspec`

    Args:
        value: A value to serialize#
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
        except KeyError:
            continue
        return encoder(value)
    raise TypeError(f"Unsupported type: {type(value)!r}")


def dec_hook(type_: Any, value: Any) -> Any:  # pragma: no cover
    """Transform values non-natively supported by `msgspec`

    Args:
        type_: Encountered type
        value: Value to coerce

    Returns:
        A `msgspec`-supported type
    """
    if issubclass(type_, BaseModel):
        return type_(**value)
    raise TypeError(f"Unsupported type: {type(value)!r}")


_msgspec_json_encoder = msgspec.json.Encoder(enc_hook=default_serializer)
_msgspec_json_decoder = msgspec.json.Decoder(dec_hook=dec_hook)
_msgspec_msgpack_encoder = msgspec.msgpack.Encoder(enc_hook=default_serializer)
_msgspec_msgpack_decoder = msgspec.msgpack.Decoder(dec_hook=dec_hook)


def encode_json(obj: Any, enc_hook: Optional[Callable[[Any], Any]] = default_serializer) -> bytes:
    """Encode a value into JSON.

    Args:
        obj: Value to encode
        enc_hook: Optional callable to support non-natively supported types

    Returns:
        JSON as bytes
    """
    if enc_hook is None or enc_hook is default_serializer:
        return _msgspec_json_encoder.encode(obj)
    return msgspec.json.encode(obj, enc_hook=enc_hook)


def decode_json(raw: Union[str, bytes]) -> Any:
    """Decode a JSON string/bytes into an object.

    Args:
        raw: Value to decode

    Returns:
        An object
    """
    return _msgspec_json_decoder.decode(raw)


def encode_msgpack(obj: Any, enc_hook: Optional[Callable[[Any], Any]] = default_serializer) -> bytes:
    """Encode a value into MessagePack.

    Args:
        obj: Value to encode
        enc_hook: Optional callable to support non-natively supported types

    Returns:
        MessagePack as bytes
    """
    if enc_hook is None or enc_hook is default_serializer:
        return _msgspec_msgpack_encoder.encode(obj)
    return msgspec.msgpack.encode(obj, enc_hook=enc_hook)


def decode_msgpack(raw: bytes) -> Any:
    """Decode a MessagePack string/bytes into an object.

    Args:
        raw: Value to decode

    Returns:
        An object
    """
    return _msgspec_msgpack_decoder.decode(raw)
