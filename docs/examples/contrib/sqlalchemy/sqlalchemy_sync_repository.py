from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel as _BaseModel
from pydantic import TypeAdapter
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from litestar import Litestar, get
from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.plugins.init import SQLAlchemyInitPlugin, SQLAlchemySyncConfig
from litestar.contrib.sqlalchemy.repository import SQLAlchemySyncRepository
from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers.http_handlers.decorators import delete, patch, post
from litestar.pagination import OffsetPagination
from litestar.params import Parameter
from litestar.repository.filters import LimitOffset

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BaseModel(_BaseModel):
    """Extend Pydantic's BaseModel to enable ORM mode"""

    model_config = {"from_attributes": True}


# the SQLAlchemy base includes a declarative model for you to use in your models.
# The `Base` class includes a `UUID` based primary key (`id`)
class AuthorModel(UUIDBase):
    # we can optionally provide the table name instead of auto-generating it
    __tablename__ = "author"  #  type: ignore[assignment]
    name: Mapped[str]
    dob: Mapped[date | None]
    books: Mapped[list[BookModel]] = relationship(back_populates="author", lazy="noload")


# The `AuditBase` class includes the same UUID` based primary key (`id`) and 2
# additional columns: `created` and `updated`. `created` is a timestamp of when the
# record created, and `updated` is the last time the record was modified.
class BookModel(UUIDAuditBase):
    __tablename__ = "book"  #  type: ignore[assignment]
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[AuthorModel] = relationship(lazy="joined", innerjoin=True, viewonly=True)


# we will explicitly define the schema instead of using DTO objects for clarity.


class Author(BaseModel):
    id: UUID | None
    name: str
    dob: date | None = None


class AuthorCreate(BaseModel):
    name: str
    dob: date | None = None


class AuthorUpdate(BaseModel):
    name: str | None = None
    dob: date | None = None


class AuthorRepository(SQLAlchemySyncRepository[AuthorModel]):
    """Author repository."""

    model_type = AuthorModel


async def provide_authors_repo(db_session: Session) -> AuthorRepository:
    """This provides the default Authors repository."""
    return AuthorRepository(session=db_session)


# we can optionally override the default `select` used for the repository to pass in
# specific SQL options such as join details
async def provide_author_details_repo(db_session: Session) -> AuthorRepository:
    """This provides a simple example demonstrating how to override the join options
    for the repository."""
    return AuthorRepository(
        statement=select(AuthorModel).options(selectinload(AuthorModel.books)),
        session=db_session,
    )


def provide_limit_offset_pagination(
    current_page: int = Parameter(ge=1, query="currentPage", default=1, required=False),
    page_size: int = Parameter(
        query="pageSize",
        ge=1,
        default=10,
        required=False,
    ),
) -> LimitOffset:
    """Add offset/limit pagination.

    Return type consumed by `Repository.apply_limit_offset_pagination()`.

    Parameters
    ----------
    current_page : int
        LIMIT to apply to select.
    page_size : int
        OFFSET to apply to select.
    """
    return LimitOffset(page_size, page_size * (current_page - 1))


class AuthorController(Controller):
    """Author CRUD"""

    dependencies = {"authors_repo": Provide(provide_authors_repo, sync_to_thread=False)}

    @get(path="/authors")
    def list_authors(
        self,
        authors_repo: AuthorRepository,
        limit_offset: LimitOffset,
    ) -> OffsetPagination[Author]:
        """List authors."""
        results, total = authors_repo.list_and_count(limit_offset)
        type_adapter = TypeAdapter(list[Author])
        return OffsetPagination[Author](
            items=type_adapter.validate_python(results),
            total=total,
            limit=limit_offset.limit,
            offset=limit_offset.offset,
        )

    @post(path="/authors")
    def create_author(
        self,
        authors_repo: AuthorRepository,
        data: AuthorCreate,
    ) -> Author:
        """Create a new author."""
        obj = authors_repo.add(
            AuthorModel(**data.model_dump(exclude_unset=True, exclude_none=True)),
        )
        authors_repo.session.commit()
        return Author.model_validate(obj)

    # we override the authors_repo to use the version that joins the Books in
    @get(
        path="/authors/{author_id:uuid}",
        dependencies={"authors_repo": Provide(provide_author_details_repo, sync_to_thread=False)},
    )
    def get_author(
        self,
        authors_repo: AuthorRepository,
        author_id: UUID = Parameter(
            title="Author ID",
            description="The author to retrieve.",
        ),
    ) -> Author:
        """Get an existing author."""
        obj = authors_repo.get(author_id)
        return Author.model_validate(obj)

    @patch(
        path="/authors/{author_id:uuid}",
        dependencies={"authors_repo": Provide(provide_author_details_repo, sync_to_thread=False)},
    )
    def update_author(
        self,
        authors_repo: AuthorRepository,
        data: AuthorUpdate,
        author_id: UUID = Parameter(
            title="Author ID",
            description="The author to update.",
        ),
    ) -> Author:
        """Update an author."""
        raw_obj = data.model_dump(exclude_unset=True, exclude_none=True)
        raw_obj.update({"id": author_id})
        obj = authors_repo.update(AuthorModel(**raw_obj))
        authors_repo.session.commit()
        return Author.model_validate(obj)

    @delete(path="/authors/{author_id:uuid}")
    def delete_author(
        self,
        authors_repo: AuthorRepository,
        author_id: UUID = Parameter(
            title="Author ID",
            description="The author to delete.",
        ),
    ) -> None:
        """Delete a author from the system."""
        _ = authors_repo.delete(author_id)
        authors_repo.session.commit()


sqlalchemy_config = SQLAlchemySyncConfig(connection_string="sqlite:///test.sqlite")  # Create 'db_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


def on_startup() -> None:
    """Initializes the database."""
    with sqlalchemy_config.get_engine().begin() as conn:
        UUIDBase.metadata.create_all(conn)


app = Litestar(
    route_handlers=[AuthorController],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
    dependencies={"limit_offset": Provide(provide_limit_offset_pagination)},
)
