from litestar import post
from litestar.params import JSONBody

from .models import User, UserDTO, UserReturnDTO


@post(dto=UserDTO, return_dto=UserReturnDTO)
def create_user(data: JSONBody[User]) -> User:
    return data
