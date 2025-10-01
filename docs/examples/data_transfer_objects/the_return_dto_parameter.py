from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, post
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    id: UUID
    name: str
    email: str
    password: str


# DTO for incoming data - accepts all fields
UserDTO = DataclassDTO[User]

# DTO for outgoing data - excludes sensitive fields like password
class UserReturnDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"password"})


@post("/", dto=UserDTO, return_dto=UserReturnDTO)
def create_user(data: User) -> User:
    """Create a new user.
    
    The dto=UserDTO parameter handles incoming JSON validation.
    The return_dto=UserReturnDTO parameter serializes the response,
    automatically excluding the password field for security.
    """
    # In a real app, you'd hash the password and save to database
    return data


app = Litestar(route_handlers=[create_user])
