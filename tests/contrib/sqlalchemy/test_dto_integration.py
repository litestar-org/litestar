from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from typing_extensions import Annotated

from litestar import get, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.types import RenameStrategy
from litestar.testing import create_test_client


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)

    # noinspection PyMethodParameters
    @declared_attr.directive
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        """Infer table name from class name."""
        return cls.__name__.lower()


class Author(Base):
    name: Mapped[str] = mapped_column(String(length=100), default="Arthur")
    date_of_birth: Mapped[str] = mapped_column(nullable=True)


class Book(Base):
    title: Mapped[str] = mapped_column(String(length=250), default="Hi")
    author_id: Mapped[str] = mapped_column(ForeignKey("author.id"), default="123")
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)
    bar: Mapped[str] = mapped_column(default="Hello")
    SPAM: Mapped[str] = mapped_column(default="Bye")
    spam_bar: Mapped[str] = mapped_column(default="Goodbye")


@pytest.mark.parametrize(
    "rename_strategy, instance, tested_fields, data",
    [
        ("camel", Book(spam_bar="star", author=Author(id="123")), ["spamBar"], {"spamBar": "star"}),
    ],
)
def test_fields_alias_generator_sqlalchemy(
    rename_strategy: RenameStrategy,
    instance: Book,
    tested_fields: list[str],
    data: dict[str, str],
) -> None:
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = SQLAlchemyDTO[Annotated[Book, config]]

    @post(dto=dto, signature_namespace={"Book": Book})
    def post_handler(data: Book) -> Book:
        assert data.bar == instance.bar
        assert data.SPAM == instance.SPAM
        return data

    @get(dto=dto, signature_namespace={"Book": Book})
    def get_handler() -> Book:
        return instance

    with create_test_client(
        route_handlers=[post_handler, get_handler],
        debug=True,
    ) as client:
        response_callback = client.get("/")
        assert all([response_callback.json()[f] == data[f] for f in tested_fields])

        response_callback = client.post("/", json=data)
        assert all([response_callback.json()[f] == data[f] for f in tested_fields])
