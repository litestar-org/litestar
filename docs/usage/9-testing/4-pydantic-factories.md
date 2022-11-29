# Using pydantic-factories

Starlite bundles the library [pydantic-factories](https://github.com/Goldziher/pydantic-factories), which offers an easy
and powerful way to generate mock data from pydantic models and dataclasses.

Let's say we have an API that talks to an external service and retrieves some data:

```python title="main.py"
from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from starlite import get


class Item(BaseModel):
    name: str


@runtime_checkable
class Service(Protocol):
    def get(self) -> Item:
        ...


@get(path="/item")
def get_item(service: Service) -> Item:
    return service.get()
```

We could test the `/item` route like so:

```python title="tests/conftest.py"
import pytest

from starlite.status_codes import HTTP_200_OK
from starlite import Provide, create_test_client

from my_app.main import Service, Item, get_item


@pytest.fixture()
def item():
    return Item(name="Chair")


def test_get_item(item: Item):
    class MyService(Service):
        def get_one(self) -> Item:
            return item

    with create_test_client(route_handlers=get_item, dependencies={"service": Provide(lambda: MyService())}) as client:
        response = client.get("/item")
        assert response.status_code == HTTP_200_OK
        assert response.json() == item.dict()
```

While we can define the test data manually, as is done in the above, this can be quite cumbersome. That's
where [pydantic-factories](https://github.com/Goldziher/pydantic-factories) library comes in. It generates mock data for
pydantic models and dataclasses based on type annotations. With it, we could rewrite the above example like so:

```python title="main.py"
from typing import Protocol, runtime_checkable

import pytest
from pydantic import BaseModel
from pydantic_factories import ModelFactory
from starlite.status_codes import HTTP_200_OK
from starlite import Provide, get
from starlite.testing import create_test_client


class Item(BaseModel):
    name: str


@runtime_checkable
class Service(Protocol):
    def get_one(self) -> Item:
        ...


@get(path="/item")
def get_item(service: Service) -> Item:
    return service.get_one()


class ItemFactory(ModelFactory[Item]):
    __model__ = Item


@pytest.fixture()
def item():
    return ItemFactory.build()


def test_get_item(item: Item):
    class MyService(Service):
        def get_one(self) -> Item:
            return item

    with create_test_client(route_handlers=get_item, dependencies={"service": Provide(lambda: MyService())}) as client:
        response = client.get("/item")
        assert response.status_code == HTTP_200_OK
        assert response.json() == item.dict()
```
