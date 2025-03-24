from advanced_alchemy.base import UUIDBase
from sqlalchemy.orm import Mapped


class TodoItem(UUIDBase):
    title: Mapped[str]
    done: Mapped[bool]
