from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class User:
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


class UserWriteDTO(DataclassDTO[User]):
    """Don't allow client to set the id."""

    config = DTOConfig(exclude={"id"})


# We need a dto for the handler to parse the request data per the configuration, however,
# we don't need a return DTO as we are returning a dataclass, and Litestar already knows
# how to serialize dataclasses.
@post("/users", dto=UserWriteDTO, return_dto=None, sync_to_thread=False)
def create_user(data: User) -> User:
    """Create an user."""
    return data


app = Litestar(route_handlers=[create_user])

# run: /users -H "Content-Type: application/json" -d '{"name":"Peter","email": "peter@example.com", "age":41}'
