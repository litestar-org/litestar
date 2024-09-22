from sqlalchemy.orm import Mapped

from litestar import Litestar, websocket_listener
from litestar.plugins.sqlalchemy import SQLAlchemyDTO, base


class User(base.UUIDBase):
    name: Mapped[str]


UserDTO = SQLAlchemyDTO[User]


@websocket_listener("/", dto=UserDTO)
async def handler(data: User) -> User:
    return data


app = Litestar([handler])
