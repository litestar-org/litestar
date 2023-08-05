from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Dict, List, Tuple

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, composite, declared_attr, mapped_column, relationship
from typing_extensions import Annotated

from litestar import get, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import DTOConfig
from litestar.dto._backend import _rename_field
from litestar.dto.types import RenameStrategy
from litestar.testing import create_test_client


class Base(DeclarativeBase):
    id: Mapped[str] = mapped_column(primary_key=True)  # pyright: ignore

    # noinspection PyMethodParameters
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Infer table name from class name."""
        return cls.__name__.lower()


class Author(Base):
    name: Mapped[str] = mapped_column(default="Arthur")  # pyright: ignore
    date_of_birth: Mapped[str] = mapped_column(nullable=True)  # pyright: ignore


class BookReview(Base):
    review: Mapped[str]  # pyright: ignore
    book_id: Mapped[str] = mapped_column(ForeignKey("book.id"), default="000")  # pyright: ignore


class Book(Base):
    title: Mapped[str] = mapped_column(String(length=250), default="Hi")  # pyright: ignore
    author_id: Mapped[str] = mapped_column(ForeignKey("author.id"), default="123")  # pyright: ignore
    first_author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)  # pyright: ignore
    reviews: Mapped[List[BookReview]] = relationship(lazy="joined", innerjoin=True)  # pyright: ignore
    bar: Mapped[str] = mapped_column(default="Hello")  # pyright: ignore
    SPAM: Mapped[str] = mapped_column(default="Bye")  # pyright: ignore
    spam_bar: Mapped[str] = mapped_column(default="Goodbye")  # pyright: ignore


@dataclass
class BookAuthorTestData:
    book_id: str = "000"
    book_title: str = "TDD Python"
    book_author_id: str = "123"
    book_author_name: str = "Harry Percival"
    book_author_date_of_birth: str = "01/01/1900"
    book_bar: str = "Hi"
    book_SPAM: str = "Bye"
    book_spam_bar: str = "GoodBye"
    book_review_id: str = "23432"
    book_review: str = "Excellent!"


@pytest.fixture
def book_json_data() -> Callable[[RenameStrategy, BookAuthorTestData], Tuple[Dict[str, Any], Book]]:
    def _generate(rename_strategy: RenameStrategy, test_data: BookAuthorTestData) -> Tuple[Dict[str, Any], Book]:
        data: Dict[str, Any] = {
            _rename_field(name="id", strategy=rename_strategy): test_data.book_id,
            _rename_field(name="title", strategy=rename_strategy): test_data.book_title,
            _rename_field(name="author_id", strategy=rename_strategy): test_data.book_author_id,
            _rename_field(name="bar", strategy=rename_strategy): test_data.book_bar,
            _rename_field(name="SPAM", strategy=rename_strategy): test_data.book_SPAM,
            _rename_field(name="spam_bar", strategy=rename_strategy): test_data.book_spam_bar,
            _rename_field(name="first_author", strategy=rename_strategy): {
                _rename_field(name="id", strategy=rename_strategy): test_data.book_author_id,
                _rename_field(name="name", strategy=rename_strategy): test_data.book_author_name,
                _rename_field(name="date_of_birth", strategy=rename_strategy): test_data.book_author_date_of_birth,
            },
            _rename_field(name="reviews", strategy=rename_strategy): [
                {
                    _rename_field(name="book_id", strategy=rename_strategy): test_data.book_id,
                    _rename_field(name="id", strategy=rename_strategy): test_data.book_review_id,
                    _rename_field(name="review", strategy=rename_strategy): test_data.book_review,
                }
            ],
        }
        book = Book(
            id=test_data.book_id,
            title=test_data.book_title,
            author_id=test_data.book_author_id,
            bar=test_data.book_bar,
            SPAM=test_data.book_SPAM,
            spam_bar=test_data.book_spam_bar,
            first_author=Author(
                id=test_data.book_author_id,
                name=test_data.book_author_name,
                date_of_birth=test_data.book_author_date_of_birth,
            ),
            reviews=[
                BookReview(id=test_data.book_review_id, review=test_data.book_review, book_id=test_data.book_id),
            ],
        )
        return data, book

    return _generate


@pytest.mark.parametrize(
    "rename_strategy",
    ("camel",),
)
def test_fields_alias_generator_sqlalchemy(
    rename_strategy: RenameStrategy,
    book_json_data: Callable[[RenameStrategy, BookAuthorTestData], Tuple[Dict[str, Any], Book]],
) -> None:
    test_data = BookAuthorTestData()
    json_data, instance = book_json_data(rename_strategy, test_data)
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = SQLAlchemyDTO[Annotated[Book, config]]

    @post(dto=dto, signature_namespace={"Book": Book})
    def post_handler(data: Book) -> Book:
        return data

    @get(dto=dto, signature_namespace={"Book": Book})
    def get_handler() -> Book:
        return instance

    with create_test_client(
        route_handlers=[post_handler, get_handler],
    ) as client:
        response_callback = client.get("/")
        assert response_callback.json() == json_data

        response_callback = client.post("/", json=json_data)
        assert response_callback.json() == json_data


def test_dto_with_association_proxy(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from typing import Final, List

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.associationproxy import AssociationProxy

from litestar import get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import dto_field

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    kw: Mapped[List[Keyword]] = relationship(secondary=lambda: user_keyword_table, info=dto_field("private"))
    # proxy the 'keyword' attribute from the 'kw' relationship
    keywords: AssociationProxy[List[str]] = association_proxy("kw", "keyword")

class Keyword(Base):
    __tablename__ = "keyword"
    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(64))

user_keyword_table: Final[Table] = Table(
    "user_keyword",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keyword.id"), primary_key=True),
)

dto = SQLAlchemyDTO[User]

@get("/", return_dto=dto)
def get_handler() -> User:
    return User(id=1, kw=[Keyword(keyword="bar"), Keyword(keyword="baz")])
"""
    )

    with create_test_client(route_handlers=[module.get_handler]) as client:
        response = client.get("/")
        assert response.json() == {"id": 1, "keywords": ["bar", "baz"]}


def test_dto_with_hybrid_property(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from litestar import get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO

class Base(DeclarativeBase):
    pass

class Interval(Base):
    __tablename__ = 'interval'

    id: Mapped[int] = mapped_column(primary_key=True)
    start: Mapped[int]
    end: Mapped[int]

    @hybrid_property
    def length(self) -> int:
        return self.end - self.start

dto = SQLAlchemyDTO[Interval]

@get("/", return_dto=dto)
def get_handler() -> Interval:
    return Interval(id=1, start=1, end=3)
"""
    )

    with create_test_client(route_handlers=[module.get_handler]) as client:
        response = client.get("/")
        assert response.json() == {"id": 1, "start": 1, "end": 3, "length": 2}


def test_dto_with_hybrid_property_expression(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import SQLColumnExpression

from litestar import get
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO

class Base(DeclarativeBase):
    pass

class Interval(Base):
    __tablename__ = 'interval'

    id: Mapped[int] = mapped_column(primary_key=True)
    start: Mapped[int]
    end: Mapped[int]

    @hybrid_property
    def length(self) -> int:
        return self.end - self.start

    @length.inplace.expression
    def _length_expression(cls) -> SQLColumnExpression[int]:
        return cls.end - cls.start

dto = SQLAlchemyDTO[Interval]

@get("/", return_dto=dto)
def get_handler() -> Interval:
    return Interval(id=1, start=1, end=3)
"""
    )

    with create_test_client(route_handlers=[module.get_handler]) as client:
        response = client.get("/")
        assert response.json() == {"id": 1, "start": 1, "end": 3, "length": 2}


def test_dto_with_hybrid_property_setter(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import SQLColumnExpression

from litestar import post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import dto_field

class Base(DeclarativeBase):
    pass

class Circle(Base):
    __tablename__ = 'circle'

    id: Mapped[int] = mapped_column(primary_key=True, info=dto_field("read-only"))
    diameter: Mapped[float] = mapped_column(info=dto_field("private"))

    @hybrid_property
    def radius(self) -> float:
        return self.diameter / 2

    @radius.inplace.setter
    def _radius_setter(self, value: float) -> None:
        self.diameter = value * 2

dto = SQLAlchemyDTO[Circle]

DIAMETER: float = 0

@post("/", dto=dto, sync_to_thread=False)
def get_handler(data: Circle) -> Circle:
    global DIAMETER
    DIAMETER = data.diameter
    data.id = 1
    return data
"""
    )

    with create_test_client(route_handlers=[module.get_handler]) as client:
        response = client.post("/", json={"radius": 5})
        assert response.json() == {"id": 1, "radius": 5}
        assert module.DIAMETER == 10


async def test_dto_with_composite_map() -> None:
    @dataclass
    class Point:
        x: int
        y: int

    class Vertex1(Base):
        start: Mapped[Point] = composite(mapped_column("x1"), mapped_column("y1"))
        end: Mapped[Point] = composite(mapped_column("x2"), mapped_column("y2"))

    dto = SQLAlchemyDTO[Vertex1]

    @post(dto=dto, signature_namespace={"Vertex": Vertex1})
    def post_handler(data: Vertex1) -> Vertex1:
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        response = client.post(
            "/",
            json={
                "id": "1",
                "start": {"x": 10, "y": 20},
                "end": {"x": 1, "y": 2},
            },
        )
        assert response.json() == {
            "id": "1",
            "start": {"x": 10, "y": 20},
            "end": {"x": 1, "y": 2},
        }


async def test_dto_with_composite_map_using_explicit_columns() -> None:
    @dataclass
    class Point:
        x: int
        y: int

    class Vertex2(Base):
        x1: Mapped[int]
        y1: Mapped[int]
        x2: Mapped[int]
        y2: Mapped[int]

        start: Mapped[Point] = composite("x1", "y1")
        end: Mapped[Point] = composite("x2", "y2")

    dto = SQLAlchemyDTO[Vertex2]

    @post(dto=dto, signature_namespace={"Vertex": Vertex2})
    def post_handler(data: Vertex2) -> Vertex2:
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        response = client.post(
            "/",
            json={
                "id": "1",
                "start": {"x": 10, "y": 20},
                "end": {"x": 1, "y": 2},
            },
        )
        assert response.json() == {
            "id": "1",
            "start": {"x": 10, "y": 20},
            "end": {"x": 1, "y": 2},
        }


async def test_dto_with_composite_map_using_hybrid_imperative_mapping() -> None:
    @dataclass
    class Point:
        x: int
        y: int

    table = Table(
        "vertices2",
        Base.metadata,
        Column("id", String, primary_key=True),
        Column("x1", Integer),
        Column("y1", Integer),
        Column("x2", Integer),
        Column("y2", Integer),
    )

    class Vertex3(Base):
        __table__ = table

        id: Mapped[str]

        start = composite(Point, table.c.x1, table.c.y1)
        end = composite(Point, table.c.x2, table.c.y2)

    dto = SQLAlchemyDTO[Vertex3]

    @post(dto=dto, signature_namespace={"Vertex": Vertex3})
    def post_handler(data: Vertex3) -> Vertex3:
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        response = client.post(
            "/",
            json={
                "id": "1",
                "start": {"x": 10, "y": 20},
                "end": {"x": 1, "y": 2},
            },
        )
        assert response.json() == {
            "id": "1",
            "start": {"x": 10, "y": 20},
            "end": {"x": 1, "y": 2},
        }


async def test_field_with_sequence_default(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from sqlalchemy import create_engine, Column, Integer, Sequence
from sqlalchemy.orm import DeclarativeBase, Mapped, sessionmaker

from litestar import Litestar, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import DTOConfig

engine = create_engine('sqlite:///:memory:', echo=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Model(Base):
    __tablename__ = "model"
    id: Mapped[int] = Column(Integer, Sequence('model_id_seq', optional=False), primary_key=True)
    val: Mapped[str]

class ModelCreateDTO(SQLAlchemyDTO[Model]):
    config = DTOConfig(exclude={"id"})

ModelReturnDTO = SQLAlchemyDTO[Model]

@post("/", dto=ModelCreateDTO, return_dto=ModelReturnDTO, sync_to_thread=False)
def post_handler(data: Model) -> Model:
    Base.metadata.create_all(engine)

    with Session() as session:
        session.add(data)
        session.commit()

    return data
    """
    )
    with create_test_client(route_handlers=[module.post_handler]) as client:
        response = client.post("/", json={"val": "value"})
        assert response.json() == {"id": 1, "val": "value"}
