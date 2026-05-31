from dataclasses import dataclass
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig, DTOData


@dataclass
class User:
    id: UUID
    name: str
    email: str


class UserWriteDTO(DataclassDTO[User]):
    """Inbound payloads cannot set the server-managed ``id`` field."""

    config = DTOConfig(exclude={"id"})


@post("/users", dto=UserWriteDTO, return_dto=None)
async def create_user(data: DTOData[User]) -> User:
    return data.create_instance(id=uuid4())


app = Litestar(route_handlers=[create_user])
