from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy.orm import Mapped

from litestar import get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import DTOConfig

from .my_lib import Base

T = TypeVar("T")


@dataclass
class WithCount(Generic[T]):
    count: int
    data: list[T]


class User(Base):
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]


class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})


@get("/users", dto=UserDTO, sync_to_thread=False)
def get_users() -> WithCount[User]:
    return WithCount(
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
