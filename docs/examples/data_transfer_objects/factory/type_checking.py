from datetime import datetime

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO
from sqlalchemy.orm import Mapped, mapped_column

from litestar import Litestar, post
from litestar.dto import dto_field

from .my_lib import Base


class User(Base):
    name: Mapped[str]
    password: Mapped[str] = mapped_column(info=dto_field("private"))
    created_at: Mapped[datetime] = mapped_column(info=dto_field("read-only"))


class Foo(Base):
    foo: Mapped[str]


UserDTO = SQLAlchemyDTO[User]


@post("/users", dto=UserDTO)
def create_user(data: Foo) -> Foo:
    return data


# This will raise an exception at handler registration time.
app = Litestar(route_handlers=[create_user])
