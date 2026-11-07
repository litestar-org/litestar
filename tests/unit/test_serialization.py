from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import msgspec

from litestar import MediaType, get
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.handlers import websocket_listener, websocket_stream
from litestar.serialization import (
    TypeEncoder,
    default_serializer,
    encode_json,
    encode_msgpack,
    get_serializer,
)
from litestar.testing import create_test_client


class Custom:
    pass


def _default(value: Any) -> Any:
    return "default"


def _json(value: Any) -> Any:
    return msgspec.Raw(b'"json"')


def _msgpack(value: Any) -> Any:
    return msgspec.Raw(msgspec.msgpack.encode("msgpack"))


def test_type_encoder_defaults() -> None:
    encoder = TypeEncoder(_default, json=_json)

    assert encoder(Custom()) == "default"
    assert encoder.json is _json
    assert encoder.msgpack is _default


def test_default_serializer_passes_encoding_to_type_encoder() -> None:
    type_encoders = {Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)}

    assert default_serializer(Custom(), type_encoders) == "default"
    assert bytes(default_serializer(Custom(), type_encoders, encoding="json")) == b'"json"'
    assert bytes(default_serializer(Custom(), type_encoders, encoding="msgpack")) == msgspec.msgpack.encode("msgpack")


def test_default_serializer_ignores_encoding_for_plain_callables() -> None:
    assert default_serializer(Custom(), {Custom: _default}, encoding="json") == "default"
    assert default_serializer(Custom(), {Custom: _default}, encoding="msgpack") == "default"


def test_get_serializer_with_encoding() -> None:
    type_encoders = {Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)}

    assert get_serializer(type_encoders)(Custom()) == "default"
    assert bytes(get_serializer(type_encoders, encoding="json")(Custom())) == b'"json"'
    assert bytes(get_serializer(type_encoders, encoding="msgpack")(Custom())) == msgspec.msgpack.encode("msgpack")
    assert get_serializer(None) is default_serializer
    assert get_serializer(None, encoding="json") is default_serializer


def test_encode_json_and_msgpack_select_encoding_specific_encoder() -> None:
    serializer = get_serializer({Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)})

    assert encode_json({"a": Custom()}, serializer) == b'{"a":"json"}'
    assert msgspec.msgpack.decode(encode_msgpack({"a": Custom()}, serializer)) == {"a": "msgpack"}


def test_encode_with_plain_callable_serializer_is_unchanged() -> None:
    def serializer(value: Any) -> Any:
        return "plain"

    assert encode_json(Custom(), serializer) == b'"plain"'
    assert msgspec.msgpack.decode(encode_msgpack(Custom(), serializer)) == "plain"


def test_type_encoder_in_app_response() -> None:
    @get("/json", media_type=MediaType.JSON)
    def json_handler() -> dict[str, Custom]:
        return {"a": Custom()}

    @get("/msgpack", media_type=MediaType.MESSAGEPACK)
    def msgpack_handler() -> dict[str, Custom]:
        return {"a": Custom()}

    type_encoders = {Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)}
    with create_test_client([json_handler, msgpack_handler], type_encoders=type_encoders) as client:
        assert client.get("/json").content == b'{"a":"json"}'
        assert msgspec.msgpack.decode(client.get("/msgpack").content) == {"a": "msgpack"}


def test_type_encoder_in_websocket_listener() -> None:
    @websocket_listener("/ws")
    def handler(data: str) -> dict[str, Custom]:
        return {"a": Custom()}

    type_encoders = {Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)}
    with create_test_client([handler], type_encoders=type_encoders) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == '{"a":"json"}'


def test_type_encoder_in_websocket_stream() -> None:
    @websocket_stream("/ws")
    async def handler() -> AsyncGenerator[dict[str, Custom], None]:
        yield {"a": Custom()}

    type_encoders = {Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)}
    with create_test_client([handler], type_encoders=type_encoders) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_text() == '{"a":"json"}'


def test_type_encoder_in_channels_plugin() -> None:
    plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        arbitrary_channels_allowed=True,
        type_encoders={Custom: TypeEncoder(_default, json=_json, msgpack=_msgpack)},
    )

    assert plugin.encode_data({"a": Custom()}) == b'{"a":"json"}'
