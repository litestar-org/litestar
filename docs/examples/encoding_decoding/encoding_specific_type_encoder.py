import msgspec

from litestar import Litestar, MediaType, get
from litestar.serialization import TypeEncoder


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


# Pre-encoded JSON bytes must not end up in a MessagePack body; MessagePack falls back to the default encoder.
point_encoder = TypeEncoder(
    lambda point: {"x": point.x, "y": point.y},
    json=lambda point: msgspec.Raw(f'{{"x":{point.x},"y":{point.y}}}'.encode()),
)


@get("/json", media_type=MediaType.JSON, sync_to_thread=False)
def get_json() -> Point:
    return Point(1, 2)


@get("/msgpack", media_type=MediaType.MESSAGEPACK, sync_to_thread=False)
def get_msgpack() -> Point:
    return Point(1, 2)


app = Litestar([get_json, get_msgpack], type_encoders={Point: point_encoder})
