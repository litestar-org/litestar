from datetime import datetime

from sqlalchemy.orm import Mapped

from litestar import Response, get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import DTOConfig

from .my_lib import Base


class User(Base):
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]


class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})


@get("/users", dto=UserDTO, sync_to_thread=False)
def get_users() -> Response[User]:
    return Response(
        content=User(
            id=1,
            name="Litestar User",
            password="xyz",
            created_at=datetime.now(),
        ),
        headers={"X-Total-Count": "1"},
    )
