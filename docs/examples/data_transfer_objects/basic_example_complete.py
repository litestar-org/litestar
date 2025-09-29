from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO
from litestar.dto.config import DTOConfig


@dataclass
class User:
    """Internal user model with all fields including sensitive data."""
    name: str
    email: str
    age: int
    password_hash: str
    is_admin: bool = False
    id: UUID = field(default_factory=uuid4)


# DTO for safely returning user data - excludes sensitive fields
class UserResponseDTO(DataclassDTO[User]):
    """DTO for user responses that excludes sensitive information."""
    config = DTOConfig(exclude={"password_hash", "is_admin"})


# DTO for receiving user input - excludes fields that shouldn't be set by clients
class UserCreateDTO(DataclassDTO[User]):
    """DTO for user creation that excludes auto-generated and sensitive fields."""
    config = DTOConfig(exclude={"id", "password_hash", "is_admin"})


@post("/users", dto=UserCreateDTO, return_dto=UserResponseDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    """
    Create a new user.
    
    The UserCreateDTO ensures clients can only provide name, email, and age.
    The UserResponseDTO ensures we only return safe fields in the response.
    """
    # In a real application, you would hash the password and save to a database
    data.password_hash = "hashed_password_here"
    return data


# Example without DTOs (NOT recommended for production)
@post("/users-unsafe", sync_to_thread=False)
def create_user_unsafe(data: User) -> User:
    """
    UNSAFE: This endpoint exposes all internal fields including sensitive data.
    Don't do this in production!
    """
    return data


app = Litestar([create_user, create_user_unsafe])

# When you POST to /users with:
# {"name": "John Doe", "email": "john@example.com", "age": 30}
#
# You get back (note: no password_hash or is_admin):
# {"name": "John Doe", "email": "john@example.com", "age": 30, "id": "..."}
#
# But if you POST to /users-unsafe, you'd see ALL fields including sensitive ones!