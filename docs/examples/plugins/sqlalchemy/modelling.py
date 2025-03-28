from sqlalchemy.orm import Mapped

from litestar.plugins.sqlalchemy import base


class TodoItem(base.UUIDBase):
    title: Mapped[str]
    done: Mapped[bool]
