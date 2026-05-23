from typing import Any, Dict

from litestar import Litestar, post
from litestar.params import MsgPackBody


@post(path="/")
async def msgpack_handler(
    data: MsgPackBody[Dict[str, Any]],
) -> Dict[str, Any]:
    # This will try to parse the request body as `MessagePack` regardless of the
    # `Content-Type`
    return data


app = Litestar(route_handlers=[msgpack_handler])
