from typing import Annotated

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, post
from litestar.dto import DTOConfig
from litestar.plugins.sqlalchemy import SQLAlchemyDTO


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[float]


WriteItemDTO = SQLAlchemyDTO[Annotated[Item, DTOConfig(exclude={"id"})]]
ReadItemDTO = SQLAlchemyDTO[Item]


@post("/items", dto=WriteItemDTO, return_dto=ReadItemDTO)
async def create_item(data: Item) -> Item:
    data.id = 1
    return data


app = Litestar(route_handlers=[create_item])
