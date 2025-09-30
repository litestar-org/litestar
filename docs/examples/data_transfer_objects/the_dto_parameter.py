from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, post
from litestar.dto import DataclassDTO


@dataclass
class User:
    id: UUID
    name: str


# Create a DTO for the User model
UserDTO = DataclassDTO[User]


@post("/users", dto=UserDTO)
def create_user(data: User) -> User:
    """Create a new user.
    
    The dto=UserDTO parameter tells Litestar to:
    1. Validate incoming JSON against the User model
    2. Convert the JSON to a User instance (available as 'data')
    3. Use the same DTO to serialize the returned User back to JSON
    """
    # In a real app, you'd save to database here
    return data


app = Litestar(route_handlers=[create_user])
