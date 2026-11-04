import dataclasses

from litestar import Litestar, get
from litestar.params import FromPath


@dataclasses.dataclass
class User:
    id: int
    name: str


USER_DB = {1: User(id=1, name="John Doe")}


@get("/user/{user_id:int}", sync_to_thread=False)
def get_user(user_id: FromPath[int]) -> User:
    return USER_DB[user_id]


app = Litestar(route_handlers=[get_user])
