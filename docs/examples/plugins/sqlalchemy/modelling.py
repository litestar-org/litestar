from sqlalchemy.orm import Mapped

from litestar.contrib.sqlalchemy.base import Base


class TodoItem(Base):
    title: Mapped[str]
    done: Mapped[bool]
