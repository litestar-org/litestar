from starlite import Body, RequestEncodingType, post
from starlite import Body, post, Starlite
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.MULTI_PART),
) -> User:
    return data


app = Starlite(route_handlers=[create_user])
