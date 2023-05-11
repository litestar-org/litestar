from typing import Dict

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post(path="/", sync_to_thread=False)
def msgpack_handler(data: Annotated[dict, Body(media_type=RequestEncodingType.MESSAGEPACK)]) -> Dict:
    # This will try to parse the request body as `MessagePack` regardless of the
    # `Content-Type`
    return data


app = Litestar(route_handlers=[msgpack_handler])
