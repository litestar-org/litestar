# SQL-Alchemy Plugin

Starlite offers extensive support for [SQLAlchemy](https://docs.sqlalchemy.org/) using with the
[`SQLAlchemyPlugin`][starlite.plugins.sql_alchemy.SQLAlchemyPlugin]. This plugin offers
support for SQLAlchemy declarative models, which can be used as if they were pydantic models. Additionally, you can
pass optional configuration to the plugin to create a DB engine / connection and setup DB sessions dependency injection.

## Basic Use

You can simply pass an instance of `SQLAlchemyPlugin` without passing config to the Starlite constructor. This will
extend support for serialization, deserialization and DTO creation for SQLAlchemy declarative models:

=== "Async"

    ```py title="Hello World"
    --8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_async.py"
    ```

=== "Sync"

    ```py title="Hello World"
    --8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_sync.py"
    ```

!!! important
    The `SQLAlchemyPlugin` supports only `declarative` style classes, it does not support the older `imperative` style
    because this style does not use classes, and is very hard to convert to pydantic correctly.

## Handling of Relationships

The SQLAlchemy plugin handles relationships by traversing and recursively converting the related tables into pydantic
models.
This approach, while powerful, poses some difficulties. For example, consider these two tables:

```python
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Pet(Base):
    __tablename__ = "pet"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Float)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="pets")


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String, default="moishe")
    pets = relationship(
        "Pet",
        back_populates="owner",
    )
```

The `User` table references the `Pet` table, which back references the `User` table. Hence, the resulting pydantic model
will include a circular reference. To avoid this, the plugin sets relationships of this kind in the pydantic model type
`Any` with a default of `None`. This means you can provide any value for them - or none at all, and validation will not
break.

Additionally, all relationships are defined as `Optional` in the pydantic model, following the assumption you might not
send complete data structures using the API.

## SQLAlchemy Config

You can also pass an instance of [`SQLAlchemyConfig`][starlite.plugins.sql_alchemy.SQLAlchemyConfig] to the plugin
constructor:

```python
from starlite import Starlite
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin, SQLAlchemyConfig

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from starlite import post

Base = declarative_base()


class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


@post(path="/companies")
async def create_company(data: Company, async_session: AsyncSession) -> Company:
    ...


app = Starlite(
    route_handlers=[],
    plugins=[
        SQLAlchemyPlugin(
            config=SQLAlchemyConfig(
                connection_string="sqlite+aiosqlite://", dependency_key="async_session"
            )
        ),
    ],
)
```

In the above, the `SQLAlchemyPlugin` will establish a db connection using the given connection string, and add a
dependency injection under the `async_session` key on the application level. See
the [API Reference][starlite.plugins.sql_alchemy.config.SQLAlchemyConfig] for a full reference of the
`SQLAlchemyConfig` kwargs.
