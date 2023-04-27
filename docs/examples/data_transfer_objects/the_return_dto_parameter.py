from litestar import post

from .models import User, UserDTO, UserReturnDTO


@post(dto=UserDTO, return_dto=UserReturnDTO)
def create_user(data: User) -> User:
    return data
