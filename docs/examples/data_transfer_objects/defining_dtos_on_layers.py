from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Controller, delete, get, post, put
from litestar.app import Litestar
from litestar.dto import DataclassDTO
from litestar.dto.config import DTOConfig


@dataclass
class User:
    """User model with all user information."""
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


class UserWriteDTO(DataclassDTO[User]):
    """DTO for writing user data - excludes the auto-generated ID."""
    config = DTOConfig(exclude={"id"})


class UserReadDTO(DataclassDTO[User]):
    """DTO for reading user data - includes all fields."""
    # In this example, we include all fields, but you might exclude
    # sensitive information in a real application


class UserController(Controller):
    """
    User controller demonstrating DTO inheritance.
    
    DTOs defined at the controller level apply to all route handlers
    unless overridden at the handler level.
    """
    # These DTOs apply to all handlers in this controller
    dto = UserWriteDTO        # Used for parsing request data
    return_dto = UserReadDTO  # Used for serializing response data

    @post("/", sync_to_thread=False)
    def create_user(self, data: User) -> User:
        """Create a new user. Uses UserWriteDTO for input, UserReadDTO for output."""
        return data

    @get("/", sync_to_thread=False)
    def get_users(self) -> list[User]:
        """Get all users. Uses UserReadDTO for output (no input DTO needed)."""
        return [User(name="Mr Sunglass", email="mr.sunglass@example.com", age=30)]

    @get("/{user_id:uuid}", sync_to_thread=False)
    def get_user(self, user_id: UUID) -> User:
        """Get a specific user. Uses UserReadDTO for output."""
        return User(id=user_id, name="Mr Sunglass", email="mr.sunglass@example.com", age=30)

    @put("/{user_id:uuid}", sync_to_thread=False)
    def update_user(self, data: User) -> User:
        """Update a user. Uses UserWriteDTO for input, UserReadDTO for output."""
        return data

    @delete("/{user_id:uuid}", return_dto=None, sync_to_thread=False)
    def delete_user(self, user_id: UUID) -> None:
        """
        Delete a user.
        
        By setting return_dto=None, we override the controller-level UserReadDTO
        and disable response serialization for this specific endpoint.
        """
        return None


app = Litestar([UserController])
