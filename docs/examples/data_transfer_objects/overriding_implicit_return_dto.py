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


@post(dto=UserDTO, return_dto=None, sync_to_thread=False)
def create_user(data: User) -> bytes:
    return data.name.encode(encoding="utf-8")


app = Litestar([create_user])
