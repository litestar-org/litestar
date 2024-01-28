from typing import Any, Dict

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post(path="/", sync_to_thread=False)
def msgpack_handler(
    data: Annotated[Dict[str, Any], Body(media_type=RequestEncodingType.MESSAGEPACK)],
) -> Dict[str, Any]:
    # This will try to parse the request body as `MessagePack` regardless of the
    # `Content-Type`
    return data


app = Litestar(route_handlers=[msgpack_handler])
