from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO


@dataclass
class User:
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


UserDTO = DataclassDTO[User]


@post("/", dto=UserDTO, return_dto=None, sync_to_thread=False)
def create_user(data: User) -> bytes:
    """Create a new user with custom response handling.
    
    The dto=UserDTO parameter handles incoming JSON validation.
    The return_dto=None parameter disables automatic response serialization,
    allowing you to return custom response formats like raw bytes.
    """
    # Process the validated user data
    # Return a custom byte response instead of serialized User data
    return data.name.encode("utf-8")


app = Litestar(route_handlers=[create_user])
