from __future__ import annotations

from starlite.enums import MediaType
from starlite.serialization import encode_for_media_type

from . import ConcreteDTO


def test_dto_encode_json() -> None:
    assert encode_for_media_type(MediaType.JSON, ConcreteDTO()) == b'{"a":1,"b":"two"}'


def test_dto_encode_msgpack() -> None:
    assert encode_for_media_type(MediaType.MESSAGEPACK, ConcreteDTO()) == b"\x82\xa1a\x01\xa1b\xa3two"
