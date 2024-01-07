from sqlalchemy.orm import Mapped

from litestar.plugins.sqlalchemy import UUIDBase


class TodoItem(UUIDBase):
    title: Mapped[str]
    done: Mapped[bool]
