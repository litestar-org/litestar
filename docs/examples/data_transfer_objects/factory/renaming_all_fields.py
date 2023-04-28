from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, dto_field

from .my_lib import Base


class User(Base):
    first_name: Mapped[str]
    password: Mapped[str] = mapped_column(info=dto_field("private"))
    created_at: Mapped[datetime] = mapped_column(info=dto_field("read-only"))


config = DTOConfig(rename_strategy="camel")
# another rename strategy with a custom callback:
# config = DTOConfig(rename_strategy=lambda x: f"-{x}-")
UserDTO = SQLAlchemyDTO[Annotated[User, config]]


@post("/users", dto=UserDTO)
def create_user(data: User) -> User:
    assert data.first_name == "Litestar User"
    data.created_at = datetime.min
    return data


app = Litestar(route_handlers=[create_user])

# run: /users -H "Content-Type: application/json" -d '{"firstName":"Litestar User","password":"xyz","createdAt":"2023-04-24T00:00:00Z"}'
