<img alt="Starlite logo" src="./starlite-logo.svg" width=100%, height="auto">

<div align="center">

![PyPI - License](https://img.shields.io/pypi/l/starlite?color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/starlite)

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)

[![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)](https://discord.gg/X3FJqy8d2j)
</div>

# Starlite

Starlite is a light, opinionated and flexible ASGI API framework built on top
of [pydantic](https://github.com/samuelcolvin/pydantic) and [Starlette](https://github.com/encode/starlette).

Check out the [Starlite documentation 📚](https://starlite-api.github.io/starlite/)

## Core Features

* 👉 Class based controllers
* 👉 Decorators based configuration
* 👉 Extended testing support
* 👉 Extensive typing support including inference, validation and parsing
* 👉 Full async (ASGI) support
* 👉 Layered dependency injection
* 👉 OpenAPI 3.1 schema generation with [Redoc](https://github.com/Redocly/redoc) UI
* 👉 Route guards based authorization
* 👉 Simple middleware and authentication
* 👉 Support for pydantic models and pydantic dataclasses
* 👉 Support for standard library dataclasses
* 👉 Support for SQLAlchemy declarative classes
* 👉 Plugin system to allow extending supported classes
* 👉 Ultra-fast json serialization and deserialization using [orjson](https://github.com/ijl/orjson)

## Installation

Using your package manager of choice:

```shell
pip install starlite
```

OR

```sh
poetry add starlite
```

OR

```sh
pipenv install starlite
```

## Minimal Example

Define your data model using pydantic or any library based on it (see for example ormar, beanie, SQLModel etc.):

```python title="my_app/models/user.py"
from pydantic import BaseModel, UUID4


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4
```

You can alternatively use a dataclass, either the standard library one or the one from pydantic:

```python title="my_app/models/user.py"
from uuid import UUID

# from pydantic.dataclasses import dataclass
from dataclasses import dataclass

@dataclass
class User:
    first_name: str
    last_name: str
    id: UUID
```

Define a Controller for your data model:

```python title="my_app/controllers/user.py"
from typing import List

from pydantic import UUID4
from starlite import Controller, Partial, get, post, put, patch, delete

from my_app.models import User


class UserController(Controller):
    path = "/users"

    @post()
    async def create_user(self, data: User) -> User:
        ...

    @get()
    async def list_users(self) -> List[User]:
        ...

    @patch(path="/{user_id:uuid}")
    async def partially_update_user(self, user_id: UUID4, data: Partial[User]) -> User:
        ...

    @put(path="/{user_id:uuid}")
    async def update_user(self, user_id: UUID4, data: User]) -> User]:
        ...

    @get(path="/{user_id:uuid}")
    async def get_user(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id:uuid}")
    async def delete_user(self, user_id: UUID4) -> User:
        ...
```

Import your controller into your application's entry-point and pass it to Starlite when instantiating your app:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.controllers.user import UserController

app = Starlite(route_handlers=[UserController])
```

To run your application, use an ASGI server such as [uvicorn](https://www.uvicorn.org/):

```shell
uvicorn my_app.main:app --reload
```

### Contributing

Starlite is open to contributions big and small. You can always [join our discord](https://discord.gg/X3FJqy8d2j) server
to discuss contributions and project maintenance. For guidelines on how to contribute, please
see [the contribution guide](CONTRIBUTING.md).
