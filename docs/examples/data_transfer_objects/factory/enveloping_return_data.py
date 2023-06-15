from dataclasses import dataclass
from datetime import datetime
from typing import Generic, List, TypeVar

from sqlalchemy.orm import Mapped

from litestar import Litestar, get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig

from .my_lib import Base

T = TypeVar("T")


@dataclass
class CountEnvelope(Generic[T]):
    count: int
    data: T


class User(Base):
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]


class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})


@get("/users", dto=UserDTO, sync_to_thread=False)
def get_users() -> CountEnvelope[List[User]]:
    return CountEnvelope(
        count=1,
        data=[
            User(
                id=1,
                name="Litestar User",
                password="xyz",
                created_at=datetime.now(),
            ),
        ],
    )


app = Litestar(route_handlers=[get_users])

# run: /users
