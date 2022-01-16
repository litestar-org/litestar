<img alt="Starlite logo" src="./images/starlite-logo.svg" width=100%, height="auto">

![PyPI - License](https://img.shields.io/pypi/l/starlite?color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/starlite)
[![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)](https://discord.gg/X3FJqy8d2j)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)


# Starlite

Starlite is a light, opinionated and flexible ASGI API framework built on top
of [pydantic](https://github.com/samuelcolvin/pydantic) and [Starlette](https://github.com/encode/starlette).

## Installation

Using your package manager of choice:

```shell
pip install starlite
```

or

```shell
poetry add starlite
```

or

```shell
pipenv install starlite
```

## Minimal Example

Define your data model using pydantic, or any library based on it (e.g., [ormar](https://github.com/collerek/ormar), 
[beanie](https://github.com/roman-right/beanie), or [SQLModel](https://github.com/tiangolo/sqlmodel)):

```python title="my_app/models/user.py"
from pydantic import BaseModel, UUID4


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4
```

Alternatively, use a dataclass:

```python title="my_app/models/user.py"
from uuid import UUID

from dataclasses import dataclass


@dataclass
class User:
    first_name: str
    last_name: str
    id: UUID
```

Then define a Controller for your data model:

```python title="my_app/controllers/user.py"
from my_app.models import User
from pydantic import UUID4

from starlite import Controller, Partial, get, post, put, patch, delete


class UserController(Controller):
    path = "/users"

    @post()
    async def create_user(self, data: User) -> User:
        ...

    @get()
    async def list_users(self) -> list[User]:
        ...

    @patch(path="/{user_id:uuid}")
    async def partially_update_user(self, user_id: UUID4, data: Partial[User]) -> User:
        ...

    @put(path="/{user_id:uuid}")
    async def update_user(self, user_id: UUID4, data: User) -> User:
        ...

    @get(path="/{user_id:uuid}")
    async def get_user(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id:uuid}")
    async def delete_user(self, user_id: UUID4) -> User:
        ...
```

And finally, import your controller into your application's entry-point 
and pass it to Starlite when instantiating your app:

```python title="my_app/main.py"
from my_app.controllers.user import UserController

from starlite import Starlite

app = Starlite(route_handlers=[UserController])
```

To run you application, use an ASGI server such as [uvicorn](https://www.uvicorn.org/):

```shell
uvicorn my_app.main:app --reload
```

## The Starlite Project

This project builds on top the [Starlette](https://github.com/encode/starlette) ASGI toolkit 
and [pydantic](https://github.com/samuelcolvin/pydantic) to create a higher-order, opinionated 
framework. The idea to use these two libraries as a basis is not new - it was first done in 
[FastAPI](https://github.com/tiangolo/fastapi), which in this regard (and some others) was a source 
of inspiration for this framework. However, Starlite is not FastAPI - it has a different design, different 
project goals and a completely different codebase.

Some differentiating factors are:

1. The goal of this project is to become a community driven project. That is, to not have a single "owner", 
   but a team of maintainers, in addition to community contributors.
2. Starlite draws inspiration from NestJS - a contemporary TypeScript framework - which places opinions and patterns at
   its core. As such, the design of the API breaks from the Starlette design and instead offers an opinionated
   alternative.
3. Finally, Python OOP is extremely powerful and versatile. While still allowing for function based endpoints, Starlite
   seeks to build on this by placing class based Controllers at its core.
