from sqlalchemy.orm import Mapped

from litestar.contrib.sqlalchemy.base import UUIDBase


class TodoItem(UUIDBase):
    title: Mapped[str]
    done: Mapped[bool]
