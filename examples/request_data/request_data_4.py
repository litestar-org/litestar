from starlite import Body, post, RequestEncodingType, Starlite
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.URL_ENCODED),
) -> User:
    return data


app = Starlite(route_handlers=[create_user])
