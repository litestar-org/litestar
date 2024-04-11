from typing import List
from uuid import UUID, uuid4

from litestar import Controller, delete, get, post, put

from .models import User, UserDTO, UserReturnDTO


class UserController(Controller):
    dto = UserDTO
    return_dto = UserReturnDTO

    @post(sync_to_thread=False)
    def create_user(self, data: User) -> User:
        return data

    @get(sync_to_thread=False)
    def get_users(self) -> List[User]:
        return [User(id=uuid4(), name="Litestar User")]

    @get("/{user_id:uuid}", sync_to_thread=False)
    def get_user(self, user_id: UUID) -> User:
        return User(id=user_id, name="Litestar User")

    @put("/{user_id:uuid}", sync_to_thread=False)
    def update_user(self, data: User) -> User:
        return data

    @delete("/{user_id:uuid}", return_dto=None, sync_to_thread=False)
    def delete_user(self, user_id: UUID) -> None:
        return None
