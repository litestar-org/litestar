# Plugins

You can extend Starlite to support non-pydantic / dataclass types using plugins.

Using plugins, you can have Starlite parse and validate inbound values (e.g. request-body data or parameters) as if they
were pydantic models, and then serialize the data into the desired model type, or list thereof. Plugins also allow you
to return an instance or list of instances of a model, and have it serialized correctly.

## Builtin Plugins

Currently, Starlite includes a single plugin `starlite.plugins.sql_alchemy.SQLAlchemyPlugin`, with other plugins being
planned / discussed - see the pinned issues in github for the current state of these.

### SQLAlchemyPlugin

To use the `SQLAlchemyPlugin` simply import it and pass it to the `Starlite` constructor:

```python title="my_app/main.py"
from starlite import Starlite
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

app = Starlite(route_handlers=[...], plugins=[SQLAlchemyPlugin()])
```

!!! note
    The `SQLAlchemyPlugin` *will not* create a DB connection, a `sessionmaker` or anything of this kind. This
    you will need to implement on your own according to the pattern of your choice, or using a 3rd party solution of some
    sort. The reason for this is that SQL Alchemy is very flexible and allows you to interact with it in various ways.
    We cannot decide upon the pattern that will fit your architecture in advance, and hence it is left to the user to decide.

You can now use SQL alchemy declarative classes as route handler parameters or return values:

```python title="my_app/company/models/company.py"
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)
```

```python title="my_app/company/endpoints.py"
from starlite import post, get

from my_app.company.models import Company

@post(path="/companies")
def create_company(data: Company) -> Company:
    ...


@get(path="/companies")
def get_companies() -> List[Company]:
    ...
```

!!! important
    The `SQLAlchemyPlugin` supports only `declarative` style classes, it does not support the older `imperative` style
    because this style does not use classes, and is very hard to convert to pydantic correctly.


### Handling of Relationships

The SQL Alchemy plugin handles relationship by traversing and recursively converting the related tables into pydantic models.
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

## Creating Plugins

A plugin is a class the implements the `starlite.plugins.base.PluginProtocol` class, which expects a generic `T`
representing the model type to be used.

To create a plugin you must implement the following methods:

```python
def to_pydantic_model_class(
    self, model_class: Type[T], **kwargs: Any
) -> Type[BaseModel]:
    """
    Given a model_class T, convert it to a subclass of the pydantic BaseModel
    """
    ...


@staticmethod
def is_plugin_supported_type(value: Any) -> bool:
    """
    Given a value of indeterminate type, determine if this value is supported by the plugin by returning a bool.
    """
    ...


def from_pydantic_model_instance(
    self, model_class: Type[T], pydantic_model_instance: BaseModel
) -> T:
    """
    Given an instance of a pydantic model created using a plugin's 'to_pydantic_model_class',
    return an instance of the class from which that pydantic model has been created.

    This class is passed in as the 'model_class' kwarg.
    """
    ...


def to_dict(self, model_instance: T) -> Dict[str, Any]:
    """
    Given an instance of a model supported by the plugin, return a dictionary of serializable values.
    """
    ...


def from_dict(self, model_class: Type[T], **kwargs: Any) -> T:
    """
    Given a class supported by this plugin and a dict of values, create an instance of the class
    """
    ...
```
