from litestar import post
from litestar.params import JSONBody

from .models import User, UserDTO


@post(dto=UserDTO, sync_to_thread=False)
def create_user(data: JSONBody[User]) -> User:
    return data
