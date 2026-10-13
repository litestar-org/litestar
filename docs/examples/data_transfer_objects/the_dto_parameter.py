from litestar import post

from .models import User, UserDTO


@post(dto=UserDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    return data
