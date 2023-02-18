from dataclasses import dataclass

from starlite import Starlite, post
from starlite.enums import RequestEncodingType
from starlite.params import Body


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
