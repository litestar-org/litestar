from typing import Dict

from starlite import Body, RequestEncodingType, Starlite, post


@post(path="/header")
def header(data: Dict) -> Dict:
    # This will try to parse the request body as `MessagePack` if a `Content-Type`
    # header with the value `application/x-msgpack` is set
    return data


@post(path="/annotated")
def annotated(data: Dict = Body(media_type=RequestEncodingType.MESSAGEPACK)) -> Dict:
    # This will try to parse the request body as `MessagePack` regardless of the
    # `Content-Type`
    return data


app = Starlite(route_handlers=[header, annotated])
