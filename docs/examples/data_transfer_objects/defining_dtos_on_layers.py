from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Controller, Litestar, delete, get, post, put
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    id: UUID
    name: str
    email: str


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
    path = "/users"
    dto = UserWriteDTO        # For incoming data (POST, PUT)
    return_dto = UserReadDTO  # For outgoing data

    @post("/")
    def create_user(self, data: User) -> User:
        # The id field is excluded from incoming data via UserWriteDTO
        # but included in the response via UserReadDTO
        return data

    @get("/")
    def get_users(self) -> list[User]:
        # Returns all users using UserReadDTO
        return []

    @put("/{user_id:uuid}")
    def update_user(self, user_id: UUID, data: User) -> User:
        # Uses controller-level DTOs
        return data

    @delete("/{user_id:uuid}", return_dto=None)
    def delete_user(self, user_id: UUID) -> None:
        # Overrides controller return_dto to disable response serialization
        return None


app = Litestar([UserController])
