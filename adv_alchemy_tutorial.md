# Advanced-Alchemy Migration Guide

This document contains all the SQLAlchemy content that was removed from Litestar v3.0 and serves as a comprehensive guide for migrating to advanced-alchemy.

## Overview

In Litestar v3.0, all SQLAlchemy functionality has been moved to the `advanced-alchemy` package. This separation provides cleaner architecture and allows the advanced-alchemy team to focus on SQLAlchemy-specific features.

## Migration Summary

### Import Changes

All imports need to be updated from Litestar to advanced-alchemy:

```python
# Before (Litestar v2)
from litestar.contrib.sqlalchemy import SQLAlchemyPlugin, SQLAlchemyAsyncConfig
from litestar.contrib.sqlalchemy.base import UUIDBase, UUIDAuditBase
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository
from litestar.plugins.sqlalchemy import SQLAlchemyInitPlugin, SQLAlchemySerializationPlugin

# After (Litestar v3 + advanced-alchemy)
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin, SQLAlchemyAsyncConfig
from advanced_alchemy.extensions.litestar.base import UUIDBase, UUIDAuditBase
from advanced_alchemy.extensions.litestar.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin, SQLAlchemySerializationPlugin
```

### Installation

Install advanced-alchemy separately:

```bash
pip install advanced-alchemy[litestar]
# or
pip install "advanced-alchemy[litestar,uuid]"  # if you need UUID support
```

## Complete Example Collection

All examples below demonstrate the full migration from Litestar's built-in SQLAlchemy support to advanced-alchemy.

### 1. Basic Declarative Models

This example shows how to define SQLAlchemy models using advanced-alchemy's base classes:

```python
from __future__ import annotations

import uuid
from datetime import date
from uuid import UUID

from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin, base
from sqlalchemy import ForeignKey, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar import Litestar, get


# The SQLAlchemy base includes a declarative model for you to use in your models.
# The `UUIDBase` class includes a `UUID` based primary key (`id`)
class Author(base.UUIDBase):
    __tablename__ = "author"
    name: Mapped[str]
    dob: Mapped[date]
    books: Mapped[list[Book]] = relationship(back_populates="author", lazy="selectin")


# The `UUIDAuditBase` class includes the same UUID` based primary key (`id`) and 2
# additional columns: `created_at` and `updated_at`. `created_at` is a timestamp of when the
# record created, and `updated_at` is the last time the record was modified.
class Book(base.UUIDAuditBase):
    __tablename__ = "book"
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True, viewonly=True)


session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config, create_all=True
)  # Create 'async_session' dependency.


async def on_startup(app: Litestar) -> None:
    """Adds some dummy data if no data is present."""
    async with sqlalchemy_config.get_session() as session:
        statement = select(func.count()).select_from(Author)
        count = await session.execute(statement)
        if not count.scalar():
            author_id = uuid.uuid4()
            session.add(Author(name="Stephen King", dob=date(1954, 9, 21), id=author_id))
            session.add(Book(title="It", author_id=author_id))
            await session.commit()


@get(path="/authors")
async def get_authors(db_session: AsyncSession, db_engine: AsyncEngine) -> list[Author]:
    """Interact with SQLAlchemy engine and session."""
    return list(await db_session.scalars(select(Author)))


app = Litestar(
    route_handlers=[get_authors],
    on_startup=[on_startup],
    debug=True,
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
)
```

### 2. Repository Pattern with CRUD Operations

This example demonstrates the repository pattern with full CRUD operations:

```python
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    base,
    filters,
    repository,
)
from pydantic import BaseModel as _BaseModel
from pydantic import TypeAdapter
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from litestar import Litestar, get
from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers.http_handlers.decorators import delete, patch, post
from litestar.pagination import OffsetPagination
from litestar.params import Parameter

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BaseModel(_BaseModel):
    """Extend Pydantic's BaseModel to enable ORM mode"""

    model_config = {"from_attributes": True}


# The SQLAlchemy base includes a declarative model for you to use in your models.
# The `UUIDBase` class includes a `UUID` based primary key (`id`)
class AuthorModel(base.UUIDBase):
    # we can optionally provide the table name instead of auto-generating it
    __tablename__ = "author"  #  type: ignore[assignment]
    name: Mapped[str]
    dob: Mapped[date | None]
    books: Mapped[list[BookModel]] = relationship(back_populates="author", lazy="noload")


# The `UUIDAuditBase` class includes the same UUID` based primary key (`id`) and 2
# additional columns: `created_at` and `updated_at`. `created_at` is a timestamp of when the
# record created, and `updated_at` is the last time the record was modified.
class BookModel(base.UUIDAuditBase):
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


class AuthorRepository(repository.SQLAlchemyAsyncRepository[AuthorModel]):
    """Author repository."""

    model_type = AuthorModel


async def provide_authors_repo(db_session: AsyncSession) -> AuthorRepository:
    """This provides the default Authors repository."""
    return AuthorRepository(session=db_session)


# we can optionally override the default `select` used for the repository to pass in
# specific SQL options such as join details
async def provide_author_details_repo(db_session: AsyncSession) -> AuthorRepository:
    """This provides a simple example demonstrating how to override the join options for the repository."""
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
) -> filters.LimitOffset:
    """Add offset/limit pagination.

    Return type consumed by `Repository.apply_limit_offset_pagination()`.

    Parameters
    ----------
    current_page : int
        LIMIT to apply to select.
    page_size : int
        OFFSET to apply to select.
    """
    return filters.LimitOffset(page_size, page_size * (current_page - 1))


class AuthorController(Controller):
    """Author CRUD"""

    dependencies = {"authors_repo": Provide(provide_authors_repo)}

    @get(path="/authors")
    async def list_authors(
        self,
        authors_repo: AuthorRepository,
        limit_offset: filters.LimitOffset,
    ) -> OffsetPagination[Author]:
        """List authors."""
        results, total = await authors_repo.list_and_count(limit_offset)
        type_adapter = TypeAdapter(list[Author])
        return OffsetPagination[Author](
            items=type_adapter.validate_python(results),
            total=total,
            limit=limit_offset.limit,
            offset=limit_offset.offset,
        )

    @post(path="/authors")
    async def create_author(
        self,
        authors_repo: AuthorRepository,
        data: AuthorCreate,
    ) -> Author:
        """Create a new author."""
        obj = await authors_repo.add(
            AuthorModel(**data.model_dump(exclude_unset=True, exclude_none=True)),
        )
        await authors_repo.session.commit()
        return Author.model_validate(obj)

    # we override the authors_repo to use the version that joins the Books in
    @get(path="/authors/{author_id:uuid}", dependencies={"authors_repo": Provide(provide_author_details_repo)})
    async def get_author(
        self,
        authors_repo: AuthorRepository,
        author_id: UUID = Parameter(
            title="Author ID",
            description="The author to retrieve.",
        ),
    ) -> Author:
        """Get an existing author."""
        obj = await authors_repo.get(author_id)
        return Author.model_validate(obj)

    @patch(
        path="/authors/{author_id:uuid}",
        dependencies={"authors_repo": Provide(provide_author_details_repo)},
    )
    async def update_author(
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
        obj = await authors_repo.update(AuthorModel(**raw_obj))
        await authors_repo.session.commit()
        return Author.from_orm(obj)

    @delete(path="/authors/{author_id:uuid}")
    async def delete_author(
        self,
        authors_repo: AuthorRepository,
        author_id: UUID = Parameter(
            title="Author ID",
            description="The author to delete.",
        ),
    ) -> None:
        """Delete a author from the system."""
        _ = await authors_repo.delete(author_id)
        await authors_repo.session.commit()


session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config
)  # Create 'db_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(base.UUIDBase.metadata.create_all)


app = Litestar(
    route_handlers=[AuthorController],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
    dependencies={"limit_offset": Provide(provide_limit_offset_pagination)},
)
```

### 3. Plugin-Based Configuration

This example shows how to use the SQLAlchemy plugin for simplified configuration:

```python
from collections.abc import AsyncGenerator
from typing import Optional

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get, post, put
from litestar.exceptions import ClientException, NotFoundException
from litestar.status_codes import HTTP_409_CONFLICT


class Base(DeclarativeBase): ...


class TodoItem(Base):
    __tablename__ = "todo_items"

    title: Mapped[str] = mapped_column(primary_key=True)
    done: Mapped[bool]


async def provide_transaction(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    try:
        async with db_session.begin():
            yield db_session
    except IntegrityError as exc:
        raise ClientException(
            status_code=HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


async def get_todo_by_title(todo_name: str, session: AsyncSession) -> TodoItem:
    query = select(TodoItem).where(TodoItem.title == todo_name)
    result = await session.execute(query)
    try:
        return result.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"TODO {todo_name!r} not found") from e


async def get_todo_list(done: Optional[bool], session: AsyncSession) -> list[TodoItem]:
    query = select(TodoItem)
    if done is not None:
        query = query.where(TodoItem.done.is_(done))

    result = await session.execute(query)
    return list(result.scalars().all())


@get("/")
async def get_list(transaction: AsyncSession, done: Optional[bool] = None) -> list[TodoItem]:
    return await get_todo_list(done, transaction)


@post("/")
async def add_item(data: TodoItem, transaction: AsyncSession) -> TodoItem:
    transaction.add(data)
    return data


@put("/{item_title:str}")
async def update_item(item_title: str, data: TodoItem, transaction: AsyncSession) -> TodoItem:
    todo_item = await get_todo_by_title(item_title, transaction)
    todo_item.title = data.title
    todo_item.done = data.done
    return todo_item


db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///todo.sqlite",
    metadata=Base.metadata,
    create_all=True,
    before_send_handler="autocommit",
)

app = Litestar(
    [get_list, add_item, update_item],
    dependencies={"transaction": provide_transaction},
    plugins=[SQLAlchemyPlugin(db_config)],
)
```

## Tutorial Content

The following sections contain the complete tutorial content that was removed from Litestar documentation.

### Introduction to SQLAlchemy with Advanced-Alchemy

When working with SQLAlchemy in Litestar applications, we use the `advanced-alchemy` package which provides seamless integration between SQLAlchemy and Litestar. This tutorial will walk you through various patterns and best practices.

#### Key Features

1. **Dependency Injection**: Automatic session management and injection
2. **Plugin System**: Easy configuration through plugins
3. **Repository Pattern**: Built-in repository classes for common operations
4. **Serialization**: Automatic handling of SQLAlchemy models

#### Essential Concepts

- **Session Management**: Sessions are automatically managed by the plugin
- **Transaction Handling**: Automatic transaction management with rollback support
- **Model Serialization**: Automatic conversion between SQLAlchemy models and Python types

### Providing Sessions with Dependency Injection

One of the key improvements when using advanced-alchemy is centralized session management through dependency injection:

```python
from collections.abc import AsyncGenerator
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.exceptions import ClientException
from litestar.status_codes import HTTP_409_CONFLICT

async def provide_transaction(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Provides a database transaction."""
    try:
        async with db_session.begin():
            yield db_session
    except IntegrityError as exc:
        raise ClientException(
            status_code=HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

# Register as a dependency
app = Litestar(
    route_handlers=[...],
    dependencies={"transaction": provide_transaction},
    plugins=[SQLAlchemyPlugin(config)],
)
```

This approach provides several benefits:

1. **Centralized Error Handling**: Handle database errors in one place
2. **Automatic Transaction Management**: Transactions are automatically committed or rolled back
3. **Reduced Boilerplate**: No need to create sessions in every handler

### Plugin Configuration Options

Advanced-alchemy provides several plugin classes for different use cases:

#### SQLAlchemyPlugin

Basic plugin for session management:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin

config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost/db",
    metadata=Base.metadata,
    create_all=True,
)

plugin = SQLAlchemyPlugin(config=config)
```

#### SQLAlchemyInitPlugin

Plugin with enhanced initialization features:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin, SQLAlchemyAsyncConfig

config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost/db",
    session_config=AsyncSessionConfig(expire_on_commit=False),
)

plugin = SQLAlchemyInitPlugin(config=config)
```

#### SQLAlchemySerializationPlugin

Plugin with automatic serialization support:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemySerializationPlugin

plugin = SQLAlchemySerializationPlugin()
```

### Repository Pattern

Advanced-alchemy provides repository base classes for common database operations:

```python
from advanced_alchemy.extensions.litestar.repository import SQLAlchemyAsyncRepository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

class AuthorRepository(SQLAlchemyAsyncRepository[AuthorModel]):
    """Author repository with custom methods."""

    model_type = AuthorModel

    async def find_by_name(self, name: str) -> AuthorModel | None:
        """Find author by name."""
        return await self.get_one_or_none(name=name)

# Dependency injection
async def provide_authors_repo(db_session: AsyncSession) -> AuthorRepository:
    return AuthorRepository(session=db_session)
```

### Bulk Operations

Repository classes support efficient bulk operations:

```python
# Bulk insert
authors = [
    AuthorModel(name="Author 1"),
    AuthorModel(name="Author 2"),
]
await repository.add_many(authors)

# Bulk update
await repository.update_many([
    {"id": author_id_1, "name": "Updated Name 1"},
    {"id": author_id_2, "name": "Updated Name 2"},
])

# Bulk delete
await repository.delete_many([author_id_1, author_id_2])
```

### Filtering and Pagination

Advanced-alchemy provides powerful filtering capabilities:

```python
from advanced_alchemy.extensions.litestar import filters

# Pagination
limit_offset = filters.LimitOffset(limit=10, offset=0)
results, total = await repository.list_and_count(limit_offset)

# Filtering
search_filter = filters.SearchFilter(field_name="name", value="John")
results = await repository.list(search_filter)

# Complex filtering
author_filter = filters.FilterTypes(
    filters=[
        filters.SearchFilter(field_name="name", value="Stephen"),
        filters.OrderBy(field_name="created_at", sort_order="desc"),
    ]
)
results = await repository.list(author_filter)
```

### Model Base Classes

Advanced-alchemy provides several base classes for common model patterns:

#### UUIDBase

Provides UUID-based primary keys:

```python
from advanced_alchemy.extensions.litestar.base import UUIDBase

class MyModel(UUIDBase):
    __tablename__ = "my_table"
    name: Mapped[str]
    # Automatically includes: id (UUID primary key)
```

#### UUIDAuditBase

Includes UUID primary key plus audit fields:

```python
from advanced_alchemy.extensions.litestar.base import UUIDAuditBase

class MyAuditedModel(UUIDAuditBase):
    __tablename__ = "my_audited_table"
    name: Mapped[str]
    # Automatically includes:
    # - id (UUID primary key)
    # - created_at (DateTime)
    # - updated_at (DateTime)
```

#### BigIntBase

Provides auto-incrementing integer primary keys:

```python
from advanced_alchemy.extensions.litestar.base import BigIntBase

class MySequentialModel(BigIntBase):
    __tablename__ = "my_sequential_table"
    name: Mapped[str]
    # Automatically includes: id (BigInteger primary key)
```

### Serialization and DTOs

Advanced-alchemy integrates with Litestar's DTO system for automatic serialization:

```python
from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO

class AuthorDTO(SQLAlchemyDTO[AuthorModel]):
    """Data transfer object for Author model."""
    config = SQLAlchemyDTOConfig(
        exclude={"books"},  # Exclude relationships for performance
    )

@get("/authors", return_dto=AuthorDTO)
async def get_authors(repo: AuthorRepository) -> list[AuthorModel]:
    return await repo.list()
```

### Advanced Configuration

#### Connection Strings

Advanced-alchemy supports various database backends:

```python
# PostgreSQL with asyncpg
connection_string = "postgresql+asyncpg://user:pass@localhost/db"

# MySQL with aiomysql
connection_string = "mysql+aiomysql://user:pass@localhost/db"

# SQLite with aiosqlite
connection_string = "sqlite+aiosqlite:///path/to/db.sqlite"
```

#### Session Configuration

Customize session behavior:

```python
from advanced_alchemy.extensions.litestar import AsyncSessionConfig

session_config = AsyncSessionConfig(
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

config = SQLAlchemyAsyncConfig(
    connection_string="...",
    session_config=session_config,
)
```

#### Engine Configuration

Configure the SQLAlchemy engine:

```python
from advanced_alchemy.extensions.litestar import EngineConfig

engine_config = EngineConfig(
    echo=True,  # Log SQL queries
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

config = SQLAlchemyAsyncConfig(
    connection_string="...",
    engine_config=engine_config,
)
```

### Testing

Advanced-alchemy provides utilities for testing:

```python
import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
from sqlalchemy.ext.asyncio import create_async_engine

@pytest.fixture
async def db_config():
    """Test database configuration."""
    return SQLAlchemyAsyncConfig(
        connection_string="sqlite+aiosqlite:///:memory:",
        create_all=True,
    )

@pytest.fixture
async def test_app(db_config):
    """Test application with in-memory database."""
    return Litestar(
        route_handlers=[...],
        plugins=[SQLAlchemyPlugin(config=db_config)],
    )
```

### Migration from Litestar Built-in SQLAlchemy

To migrate from Litestar's built-in SQLAlchemy support:

1. **Install advanced-alchemy**:
   ```bash
   pip install advanced-alchemy[litestar]
   ```

2. **Update imports**:
   ```python
   # Old
   from litestar.contrib.sqlalchemy import *
   from litestar.plugins.sqlalchemy import *

   # New
   from advanced_alchemy.extensions.litestar import *
   ```

3. **Update configuration**:
   ```python
   # Old
   from litestar.contrib.sqlalchemy import SQLAlchemyConfig

   # New
   from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
   ```

4. **No code changes needed**: The API is the same, only the import paths change.

### Best Practices

1. **Use Repository Pattern**: Encapsulate database operations in repository classes
2. **Leverage Dependency Injection**: Use DI for session and repository management
3. **Handle Transactions Properly**: Use context managers for transaction management
4. **Use DTOs for Serialization**: Define DTOs for clean API boundaries
5. **Configure Connection Pooling**: Set appropriate pool sizes for production
6. **Use Migrations**: Use Alembic for database schema management
7. **Test with In-Memory Databases**: Use SQLite in-memory for fast tests

### Common Patterns

#### Health Check Endpoint

```python
@get("/health/db")
async def db_health_check(db_session: AsyncSession) -> dict[str, str]:
    """Check database connectivity."""
    try:
        await db_session.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

#### Soft Delete Pattern

```python
from advanced_alchemy.extensions.litestar.base import UUIDAuditBase
from sqlalchemy import DateTime
from datetime import datetime

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

class User(UUIDAuditBase, SoftDeleteMixin):
    __tablename__ = "users"
    name: Mapped[str]
```

#### Optimistic Locking

```python
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

class VersionedModel(UUIDBase):
    version: Mapped[int] = mapped_column(Integer, default=1)

    def increment_version(self):
        self.version += 1
```

This completes the comprehensive migration guide. All the functionality that was available in Litestar's built-in SQLAlchemy support is available in advanced-alchemy with the same API, just with different import paths.

### Documentation Resources

- [Advanced-Alchemy Documentation](https://docs.advanced-alchemy.litestar.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Litestar Documentation](https://docs.litestar.dev/)

For questions and support, visit the [Advanced-Alchemy GitHub repository](https://github.com/litestar-org/advanced-alchemy).