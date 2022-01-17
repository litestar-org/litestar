# Data Transfer Objects (DTOs)

Starlite includes a `DTOFactory` class that allows you to create DTOs from pydantic models, dataclasses and any other
class supported via plugins.

An instance of the factory must first be created, optionally passing plugins to it as a kwarg. It can then be used to
create a DTO by calling the instance like a function. Additionally, it can exclude (drop) attributes specifies in the '
exclude' list and remap field names and/or field types.

The created DTO can be used for data parsing, validation and OpenAPI schema generation like a regularly declared
pydantic model.

!!! important
    Although the value generated is a pydantic factory, because it is being generated programmatically, it's
    currently impossible to extend editor auto-complete for the DTO properties - it will be typed as `Any`.

For example, given a pydantic model

```python
from pydantic import BaseModel
from starlite import DTOFactory


class MyClass(BaseModel):
    first: int
    second: int


MyClassDTOFactory = DTOFactory()

MyClassDTO = MyClassDTOFactory(
    "MyClassDTO", MyClass, exclude=["first"], field_mapping={"second": ("third", float)}
)
```

`MyClassDTO` is now equal to this:

```python
from pydantic import BaseModel


class MyClassDTO(BaseModel):
    third: float
```

It can be used as a regular pydantic model, e.g.:

```python
from pydantic import BaseModel
from starlite import DTOFactory, post


class MyClass(BaseModel):
    first: int
    second: int


MyClassDTOFactory = DTOFactory()

MyClassDTO = MyClassDTOFactory(
    "MyClassDTO", MyClass, exclude=["first"], field_mapping={"second": ("third", float)}
)


@post(path="/my-path")
def create_obj(data: MyClassDTO) -> MyClass:
    ...
```

The `DTOFactory` class can also be instantiated with [plugins](10-plugins.md), for example - here is a factory that
support SQL Alchemy declarative classes:

```python
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base
from starlite import DTOFactory
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin


SQLAlchemyDTOFactory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


CompanyDTO = SQLAlchemyDTOFactory("CompanyDTO", Company, exclude=["id"])
```
