from typing import Dict

from starlite import Starlite, post
from starlite.enums import RequestEncodingType
from starlite.params import Body


@post(path="/")
def msgpack_handler(data: Dict = Body(media_type=RequestEncodingType.MESSAGEPACK)) -> Dict:
    # This will try to parse the request body as `MessagePack` regardless of the
    # `Content-Type`
    return data


app = Starlite(route_handlers=[msgpack_handler])
