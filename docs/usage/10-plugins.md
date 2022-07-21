# Plugins

You can extend Starlite to support non-pydantic / dataclass types using plugins.

Using plugins, you can have Starlite parse and validate inbound values (e.g. request-body data or parameters) as if they
were pydantic models, and then serialize the data into the desired model type, or list thereof. Plugins also allow you
to return an instance or list of instances of a model, and have it serialized correctly.

## Builtin Plugins

### SQLAlchemyPlugin

To use the `SQLAlchemyPlugin` import it and pass it to the `Starlite` constructor:

```python title="my_app/main.py"
from starlite import Starlite
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

app = Starlite(route_handlers=[...], plugins=[SQLAlchemyPlugin()])
```

<!-- prettier-ignore -->
!!! note
    The `SQLAlchemyPlugin` _will not_ create a DB connection, a `sessionmaker` or anything of this kind. This
    you will need to implement on your own according to the pattern of your choice, or using a 3rd party solution of some
    sort.

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

<!-- prettier-ignore -->
!!! important
    The `SQLAlchemyPlugin` supports only `declarative` style classes, it does not support the older `imperative` style
    because this style does not use classes, and is very hard to convert to pydantic correctly.

#### Handling of Relationships

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

### Tortoise ORM Plugin

To use the `TortoiseORMPlguin` import it and pass it to the `Starlite` constructor:

```python
from typing import List, cast

from tortoise import Model, Tortoise, fields

from starlite import Starlite, get, post
from starlite.plugins.tortoise_orm import TortoiseORMPlugin


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    optional = fields.TextField(null=True)
    events: fields.ReverseRelation["Event"]

    class Meta:
        ordering = ["name"]


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )
    address: fields.OneToOneNullableRelation["Address"]

    class Meta:
        ordering = ["name"]


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    class Meta:
        ordering = ["city"]


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ManyToManyRelation[Event]

    class Meta:
        ordering = ["name"]


async def init_tortoise() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
    await Tortoise.generate_schemas()


@get("/tournaments")
async def get_tournaments() -> List[Tournament]:
    tournaments = await Tournament.all()
    return cast(List[Tournament], tournaments)


@get("/tournaments/{tournament_id:int}")
async def get_tournament(tournament_id: int) -> Tournament:
    tournament = await Tournament.filter(id=tournament_id).first()
    return cast(Tournament, tournament)


@post("/tournaments")
async def create_tournament(data: Tournament) -> Tournament:
    assert isinstance(data, Tournament)
    await data.save()
    await data.refresh_from_db()
    return data


app = Starlite(
    route_handlers=[get_tournament, get_tournaments, create_tournament],
    on_startup=[init_tortoise],
    plugins=[TortoiseORMPlugin()],
)
```

With the plugin in place, you can use any Tortoise model as type in route handelrs.

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
