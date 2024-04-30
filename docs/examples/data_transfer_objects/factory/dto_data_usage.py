from dataclasses import dataclass
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig, DTOData


@dataclass
class User:
    name: str
    email: str
    age: int
    id: UUID


class UserWriteDTO(DataclassDTO[User]):
    """Don't allow client to set the id."""

    config = DTOConfig(exclude={"id"})


@post("/users", dto=UserWriteDTO, return_dto=None, sync_to_thread=False)
def create_user(data: DTOData[User]) -> User:
    """Create an user."""
    return data.create_instance(id=uuid4())


app = Litestar(route_handlers=[create_user])

# run: /users -H "Content-Type: application/json" -d '{"name":"Peter", "email": "peter@example.com", "age":41}'
