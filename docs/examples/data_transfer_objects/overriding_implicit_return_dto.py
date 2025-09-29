from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO


@dataclass
class User:
    """User model with complete user information."""
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


# DTO for parsing incoming user data
UserDTO = DataclassDTO[User]


@post("/users", dto=UserDTO, return_dto=None, sync_to_thread=False)
def create_user(data: User) -> bytes:
    """
    Create a user and return custom response data.
    
    By setting return_dto=None, we disable automatic serialization of the
    response. This means we must return a type that Litestar can directly
    convert to bytes (like str, bytes, dict, etc.).
    
    This is useful when you want complete control over the response format
    or when you're returning non-standard data.
    """
    # Custom response logic - in this case, just return the user's name as bytes
    # In a real application, you might return a custom success message,
    # redirect to another endpoint, or return a specialized response format
    return f"User '{data.name}' created successfully!".encode(encoding="utf-8")


app = Litestar([create_user])

# When you POST to /users with:
# {"name": "Charlie", "email": "charlie@example.com", "age": 28}
#
# You get back the plain text response:
# "User 'Charlie' created successfully!"
#
# Instead of the usual JSON representation of the User object
