from datetime import datetime

from advanced_alchemy.dto import SQLAlchemyDTO
from sqlalchemy.orm import Mapped

from litestar.dto import DTOConfig

from .my_lib import Base


class User(Base):
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]


class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})
