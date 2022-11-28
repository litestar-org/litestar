from pydantic import BaseModel

from starlite import Starlite, get

USER_DB = {1: {"id": 1, "name": "John Doe"}}


class User(BaseModel):
    id: int
    name: str


@get("/user/{user_id:int}")
def get_user(user_id: int) -> User:
    return User.parse_obj(USER_DB[user_id])


app = Starlite(route_handlers=[get_user])
