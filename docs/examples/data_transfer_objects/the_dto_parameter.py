from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import post
from litestar.dto import DataclassDTO


@dataclass
class User:
    """User model representing our internal data structure."""
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


# Create a DTO that handles both input validation and output serialization
UserDTO = DataclassDTO[User]


@post("/users", dto=UserDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    """
    Create a new user.
    
    The UserDTO handles:
    1. Parsing incoming JSON into a User instance (injected as 'data')
    2. Converting the returned User instance back to JSON for the response
    """
    # In a real app, you might save to a database here
    return data

# When you POST to /users with:
# {"name": "Alice", "email": "alice@example.com", "age": 25}
#
# The DTO automatically:
# - Validates the input data
# - Creates a User instance with a generated UUID
# - Returns the complete user data as JSON
