# SQL-Alchemy Plugin

To use the `starlite.plugins.sql_alchemy.SQLAlchemyPlugin` import it and pass it to the `Starlite` constructor:

```python
from starlite import Starlite
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base
from starlite import post, get

Base = declarative_base()


class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


@post(path="/companies")
def create_company(data: Company) -> Company:
    ...


@get(path="/companies")
def get_companies() -> list[Company]:
    ...


app = Starlite(
    route_handlers=[create_company, get_companies], plugins=[SQLAlchemyPlugin()]
)
```

<!-- prettier-ignore -->
!!! important
    The `SQLAlchemyPlugin` supports only `declarative` style classes, it does not support the older `imperative` style
    because this style does not use classes, and is very hard to convert to pydantic correctly.

## Handling of Relationships

The SQLAlchemy plugin handles relationships by traversing and recursively converting the related tables into pydantic models.
This approach, while powerful, poses some difficulties. For example, consider these two tables:

```python
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Pet(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Float)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="pets")


class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String, default="moishe")
    pets = relationship(
        "Pet",
        back_populates="owner",
    )
```

The `User` table references the `Pet` table, which back references the `User` table. Hence, the resulting pydantic model
will include a circular reference. To avoid this, the plugin sets relationships of this kind in the pydantic model type
`Any` with a default of `None`. This means you can provide any value for them - or none at all, and validation will not break.

Additionally, all relationships are defined as `Optional` in the pydantic model, following the assumption you might not
send complete data structures using the API.
