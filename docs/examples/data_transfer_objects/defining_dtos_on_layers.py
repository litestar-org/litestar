from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Controller, Litestar, delete, get, post, put
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


# DTO for write operations - excludes auto-generated fields like id
class UserWriteDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"id"})


# DTO for read operations - includes all fields
class UserReadDTO(DataclassDTO[User]):
    pass


class UserController(Controller):
    """User management controller.
    
    DTOs are defined at the controller level and apply to all routes
    unless explicitly overridden on individual route handlers.
    """
    path = "/"
    dto = UserWriteDTO  # For incoming data (POST, PUT)
    return_dto = UserReadDTO  # For outgoing data

    @post("/", sync_to_thread=False)
    def create_user(self, data: User) -> User:
        # The id field is excluded from incoming data via UserWriteDTO
        # but included in the response via UserReadDTO
        return data

    @get("/", sync_to_thread=False)
    def get_users(self) -> list[User]:
        # Returns all users using UserReadDTO
        return [
            User(
                id=UUID("a3cad591-5b01-4341-ae8f-94f78f790674"),
                name="Mr Sunglass",
                email="mr.sunglass@example.com",
                age=30,
            )
        ]

    @get("/{user_id:uuid}", sync_to_thread=False)
    def get_user(self, user_id: UUID) -> User:
        # Returns specific user using UserReadDTO
        return User(id=user_id, name="Mr Sunglass", email="mr.sunglass@example.com", age=30)

    @put("/{user_id:uuid}", sync_to_thread=False)
    def update_user(self, user_id: UUID, data: User) -> User:
        # Uses controller-level DTOs
        data.id = user_id
        return data

    @delete("/{user_id:uuid}", return_dto=None, sync_to_thread=False)
    def delete_user(self, user_id: UUID) -> None:
        # Overrides controller return_dto to disable response serialization
        return None


app = Litestar(route_handlers=[UserController])
