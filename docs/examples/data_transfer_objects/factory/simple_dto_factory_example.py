from datetime import datetime

from sqlalchemy.orm import Mapped

from litestar import Litestar, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO

from .my_lib import Base


class User(Base):
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]


UserDTO = SQLAlchemyDTO[User]


@post("/users", dto=UserDTO)
def create_user(data: User) -> User:
    return data


app = Litestar(route_handlers=[create_user])

# run: /users -H "Content-Type: application/json" -d '{"name":"Litestar User","password":"xyz","created_at":"2023-04-24T00:00:00Z"}'
