from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from typing_extensions import Annotated

from litestar import post
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


class Foo(Base):
    bar: Mapped[str]
    SPAM: Mapped[str]
    spam_bar: Mapped[str]


@pytest.mark.parametrize(
    "rename_strategy, instance, tested_fields, data",
    [
        ("upper", Foo(bar="hi"), ["BAR"], {"BAR": "hi"}),
        ("lower", Foo(SPAM="goodbye"), ["spam"], {"spam": "goodbye"}),
        (lambda x: x[::-1], Foo(bar="h", SPAM="bye!"), ["rab", "MAPS"], {"rab": "h", "MAPS": "bye!"}),
        ("camel", Foo(spam_bar="star"), ["spamBar"], {"spamBar": "star"}),
        ("pascal", Foo(spam_bar="star"), ["SpamBar"], {"SpamBar": "star"}),
    ],
)
def test_fields_alias_generator_sqlalchemy(
    rename_strategy: RenameStrategy,
    instance: Foo,
    tested_fields: list[str],
    data: dict[str, str],
) -> None:
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = SQLAlchemyDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Foo:
        assert data.bar == instance.bar
        assert data.SPAM == instance.SPAM
        return data

    with create_test_client(
        route_handlers=[
            handler,
        ],
        debug=True,
    ) as client:
        response_callback = client.post("/", json=data)
        assert all([response_callback.json()[f] == data[f] for f in tested_fields])
