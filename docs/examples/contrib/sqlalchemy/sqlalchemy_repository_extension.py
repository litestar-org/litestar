from __future__ import annotations

import random
import re
import string
import unicodedata
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel as _BaseModel
from pydantic import TypeAdapter
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column
from sqlalchemy.types import String

from litestar import Litestar, get, post
from litestar.contrib.sqlalchemy.base import UUIDAuditBase
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from litestar.contrib.sqlalchemy.repository import (
    ModelT,
    SQLAlchemyAsyncRepository,
)
from litestar.di import Provide

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BaseModel(_BaseModel):
    """Extend Pydantic's BaseModel to enable ORM mode"""

    model_config = {"from_attributes": True}


# we are going to add a simple "slug" to our model that is a URL safe surrogate key to
# our database record.
@declarative_mixin
class SlugKey:
    """Slug unique Field Model Mixin."""

    __abstract__ = True
    slug: Mapped[str] = mapped_column(String(length=100), nullable=False, unique=True, sort_order=-9)


# this class can be re-used with any model that has the `SlugKey` Mixin
class SQLAlchemyAsyncSlugRepository(SQLAlchemyAsyncRepository[ModelT]):
    """Extends the repository to include slug model features.."""

    async def get_available_slug(
        self,
        value_to_slugify: str,
        **kwargs: Any,
    ) -> str:
        """Get a unique slug for the supplied value.

        If the value is found to exist, a random 4 digit character is appended to the end.
        There may be a better way to do this, but I wanted to limit the number of
        additional database calls.

        Args:
            value_to_slugify (str): A string that should be converted to a unique slug.
            **kwargs: stuff

        Returns:
            str: a unique slug for the supplied value. This is safe for URLs and other
            unique identifiers.
        """
        slug = self._slugify(value_to_slugify)
        if await self._is_slug_unique(slug):
            return slug
        # generate a random 4 digit alphanumeric string to make the slug unique and
        # avoid another DB lookup.
        random_string = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{slug}-{random_string}"

    @staticmethod
    def _slugify(value: str) -> str:
        """slugify.

        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.

        Args:
            value (str): the string to slugify

        Returns:
            str: a slugified string of the value parameter
        """
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^\w\s-]", "", value.lower())
        return re.sub(r"[-\s]+", "-", value).strip("-_")

    async def _is_slug_unique(
        self,
        slug: str,
        **kwargs: Any,
    ) -> bool:
        return await self.get_one_or_none(slug=slug) is None


# The `AuditBase` class includes the same UUID` based primary key (`id`) and 2
# additional columns: `created` and `updated`. `created` is a timestamp of when the
# record created, and `updated` is the last time the record was modified.
class BlogPost(UUIDAuditBase, SlugKey):
    title: Mapped[str]
    content: Mapped[str]


class BlogPostRepository(SQLAlchemyAsyncSlugRepository[BlogPost]):
    """Blog Post repository."""

    model_type = BlogPost


class BlogPostDTO(BaseModel):
    id: UUID | None
    slug: str
    title: str
    content: str


class BlogPostCreate(BaseModel):
    title: str
    content: str


# we can optionally override the default `select` used for the repository to pass in
# specific SQL options such as join details
async def provide_blog_post_repo(db_session: AsyncSession) -> BlogPostRepository:
    """This provides a simple example demonstrating how to override the join options
    for the repository."""
    return BlogPostRepository(session=db_session)


session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config
)  # Create 'async_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.create_all)


@get(path="/")
async def get_blogs(
    blog_post_repo: BlogPostRepository,
) -> list[BlogPostDTO]:
    """Interact with SQLAlchemy engine and session."""
    objs = await blog_post_repo.list()
    type_adapter = TypeAdapter(list[BlogPostDTO])
    return type_adapter.validate_python(objs)


@get(path="/{post_slug:str}")
async def get_blog_details(
    post_slug: str,
    blog_post_repo: BlogPostRepository,
) -> BlogPostDTO:
    """Interact with SQLAlchemy engine and session."""
    obj = await blog_post_repo.get_one(slug=post_slug)
    return BlogPostDTO.model_validate(obj)


@post(path="/")
async def create_blog(
    blog_post_repo: BlogPostRepository,
    data: BlogPostCreate,
) -> BlogPostDTO:
    """Create a new blog post."""
    _data = data.model_dump(exclude_unset=True, by_alias=False, exclude_none=True)
    _data["slug"] = await blog_post_repo.get_available_slug(_data["title"])
    obj = await blog_post_repo.add(BlogPost(**_data))
    await blog_post_repo.session.commit()
    return BlogPostDTO.model_validate(obj)


app = Litestar(
    route_handlers=[create_blog, get_blogs, get_blog_details],
    dependencies={"blog_post_repo": Provide(provide_blog_post_repo, sync_to_thread=False)},
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
)
