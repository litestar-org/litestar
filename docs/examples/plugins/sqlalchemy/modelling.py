from litestar.contrib.sqlalchemy.base import Base

from sqlalchemy.orm import Mapped


class TodoItem(Base):
    title: Mapped[str]
    done: Mapped[bool]
