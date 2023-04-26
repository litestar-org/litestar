from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, dto_field

from .my_lib import Base


class User(Base):
    name: Mapped[str]
    password: Mapped[str] = mapped_column(info=dto_field("private"))
    created_at: Mapped[datetime] = mapped_column(info=dto_field("read-only"))


UserDTO = SQLAlchemyDTO[User]
ReadUserDTO = SQLAlchemyDTO[Annotated[User, DTOConfig(exclude={"id"})]]


@post("/users", dto=UserDTO, return_dto=ReadUserDTO)
def create_user(data: User) -> User:
    data.created_at = datetime.min
    return data


app = Litestar(route_handlers=[create_user])

# run: /users -H "Content-Type: application/json" -d '{"name":"Litestar User","password":"xyz","created_at":"2023-04-24T00:00:00Z"}'
