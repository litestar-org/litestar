from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped


class TodoItem(base.UUIDBase):
    title: Mapped[str]
    done: Mapped[bool]
