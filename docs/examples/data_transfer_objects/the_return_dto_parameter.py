from litestar import post

from .models import User, UserDTO, UserReturnDTO


@post(dto=UserDTO, return_dto=UserReturnDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    return data
