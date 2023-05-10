from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import pytest
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from typing_extensions import Annotated

from litestar import get, post
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig
from litestar.dto.factory._backends.utils import RenameStrategies
from litestar.dto.factory.types import RenameStrategy
from litestar.testing import create_test_client


class Base(DeclarativeBase):
    id: Mapped[str] = mapped_column(primary_key=True)

    # noinspection PyMethodParameters
    @declared_attr.directive
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        """Infer table name from class name."""
        return cls.__name__.lower()


class Author(Base):
    name: Mapped[str] = mapped_column(default="Arthur")
    date_of_birth: Mapped[str] = mapped_column(nullable=True)


class BookReview(Base):
    review: Mapped[str]
    book_id: Mapped[str] = mapped_column(ForeignKey("book.id"), default="000")


class Book(Base):
    title: Mapped[str] = mapped_column(String(length=250), default="Hi")
    author_id: Mapped[str] = mapped_column(ForeignKey("author.id"), default="123")
    first_author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)
    reviews: Mapped[List[BookReview]] = relationship(lazy="joined", innerjoin=True)
    bar: Mapped[str] = mapped_column(default="Hello")
    SPAM: Mapped[str] = mapped_column(default="Bye")
    spam_bar: Mapped[str] = mapped_column(default="Goodbye")


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
            RenameStrategies(rename_strategy)("id"): test_data.book_id,
            RenameStrategies(rename_strategy)("title"): test_data.book_title,
            RenameStrategies(rename_strategy)("author_id"): test_data.book_author_id,
            RenameStrategies(rename_strategy)("bar"): test_data.book_bar,
            RenameStrategies(rename_strategy)("SPAM"): test_data.book_SPAM,
            RenameStrategies(rename_strategy)("spam_bar"): test_data.book_spam_bar,
            RenameStrategies(rename_strategy)("first_author"): {
                RenameStrategies(rename_strategy)("id"): test_data.book_author_id,
                RenameStrategies(rename_strategy)("name"): test_data.book_author_name,
                RenameStrategies(rename_strategy)("date_of_birth"): test_data.book_author_date_of_birth,
            },
            RenameStrategies(rename_strategy)("reviews"): [
                {
                    RenameStrategies(rename_strategy)("book_id"): test_data.book_id,
                    RenameStrategies(rename_strategy)("id"): test_data.book_review_id,
                    RenameStrategies(rename_strategy)("review"): test_data.book_review,
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
    [
        ("camel"),
    ],
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
        debug=True,
    ) as client:
        response_callback = client.get("/")
        assert response_callback.json() == json_data

        response_callback = client.post("/", json=json_data)
        assert response_callback.json() == json_data
