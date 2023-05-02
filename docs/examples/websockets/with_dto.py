from sqlalchemy.orm import Mapped

from litestar import Litestar, websocket_listener
from litestar.contrib.sqlalchemy.base import Base
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO


class User(Base):
    name: Mapped[str]


UserDTO = SQLAlchemyDTO[User]


@websocket_listener("/", dto=UserDTO)
async def handler(data: User) -> User:
    return data


app = Litestar([handler])
