from dataclasses import asdict, is_dataclass
from pathlib import PurePath, PurePosixPath
from typing import Any, Callable, Optional, Union
from uuid import UUID

import msgspec
from pydantic import BaseModel, SecretStr


def default_serializer(value: Any) -> Any:
    """Return the default serializer for a given object based on its type.

    Args:
        value: A value to serialize
    Returns:
        A serialized value
    Raises:
        TypeError: if value is not supported
    """
    if isinstance(value, BaseModel):
        return value.dict()
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, (PurePath, PurePosixPath)):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Unsupported type: {type(value)!r}")


def dec_hook(type_: Any, value: Any) -> Any:
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
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
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


def decode_msgpack(raw: Union[str, bytes]) -> Any:
    """Decode a MessagePack string/bytes into an object.

    Args:
        raw: Value to decode

    Returns:
        An object
    """
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return _msgspec_msgpack_decoder.decode(raw)
