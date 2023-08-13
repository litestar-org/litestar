from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from litestar import get
from litestar.contrib.sqlalchemy.base import UUIDAuditBase
from litestar.contrib.sqlalchemy.plugins import SQLAlchemySerializationPlugin
from litestar.pagination import ClassicPagination
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable

    from litestar.testing import RequestFactory


async def test_serialization_plugin(
    create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    module = create_module(
        """
from __future__ import annotations

from typing import List

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get, post
from litestar.contrib.sqlalchemy.plugins import SQLAlchemySerializationPlugin

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    a: Mapped[str]

@post("/a")
def post_handler(data: A) -> A:
    return data

@get("/a")
def get_handler() -> List[A]:
    return [A(id=1, a="test"), A(id=2, a="test2")]

@get("/a/1")
def get_a() -> A:
    return A(id=1, a="test")
"""
    )
    with create_test_client(
        route_handlers=[module.post_handler, module.get_handler, module.get_a],
        plugins=[SQLAlchemySerializationPlugin()],
    ) as client:
        response = client.post("/a", json={"id": 1, "a": "test"})
        assert response.status_code == 201
        assert response.json() == {"id": 1, "a": "test"}
        response = client.get("/a")
        assert response.json() == [{"id": 1, "a": "test"}, {"id": 2, "a": "test2"}]
        response = client.get("/a/1")
        assert response.json() == {"id": 1, "a": "test"}


class User(UUIDAuditBase):
    first_name: Mapped[str] = mapped_column(String(200))


def test_pagination_serialization() -> None:
    users = [User(first_name="ASD"), User(first_name="qwe")]

    @get("/paginated")
    async def paginated_handler() -> ClassicPagination[User]:
        return ClassicPagination[User](items=users, page_size=2, current_page=1, total_pages=1)

    with create_test_client(paginated_handler, plugins=[SQLAlchemySerializationPlugin()]) as client:
        response = client.get("/paginated")
        assert response.status_code == HTTP_200_OK
