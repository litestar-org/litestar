from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, post
from litestar.dto import DataclassDTO


@dataclass
class User:
    id: UUID
    name: str


UserDTO = DataclassDTO[User]


@post("/users", dto=UserDTO, return_dto=None)
def create_user(data: User) -> bytes:
    """Create a new user with custom response handling.
    
    The dto=UserDTO parameter handles incoming JSON validation.
    The return_dto=None parameter disables automatic response serialization,
    allowing you to return custom response formats like raw bytes.
    """
    # Process the validated user data
    # Return a custom byte response instead of serialized User data
    return f"User {data.name} created successfully".encode("utf-8")


app = Litestar([create_user])
