from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, base
from sqlalchemy.orm import Mapped

from litestar import Litestar, websocket_listener


class User(base.UUIDBase):
    name: Mapped[str]


UserDTO = SQLAlchemyDTO[User]


@websocket_listener("/", dto=UserDTO)
async def handler(data: User) -> User:
    return data


app = Litestar([handler])
