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

Check out the [Starlite documentation](https://goldziher.github.io/starlite/).

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
from pydantic import UUID4
from starlite.controller import Controller
from starlite.handlers import get, post, put, patch, delete
from starlite.types import Partial

from my_app.models import User


class UserController(Controller):
    path = "/users"

    @post()
    async def create(self, data: User) -> User:
        ...

    @get()
    async def get_users(self) -> list[User]:
        ...

    @patch(path="/{user_id:uuid}")
    async def partial_update_user(self, user_id: UUID4, data: Partial[User]) -> User:
        ...

    @put(path="/{user_id:uuid}")
    async def update_user(self, user_id: UUID4, data: list[User]) -> list[User]:
        ...

    @get(path="/{user_id:uuid}")
    async def get_user_by_id(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id:uuid}")
    async def delete_user_by_id(self, user_id: UUID4) -> User:
        ...

```

Import your controller into your application's entry-point and pass it to Starlite when instantiating your app:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.controllers.user import UserController

app = Starlite(route_handlers=[UserController])
```

To run you application, use an ASGI server such as [uvicorn](https://www.uvicorn.org/):

```shell
uvicorn my_app.main:app --reload
```

## Project and Roadmap

This project builds on top the Starlette ASGI toolkit and pydantic modelling to create a higher-order opinionated
framework. The idea to use these two libraries as a basis is of course not new - it was first done in FastAPI, which in
this regard (and some others) was a source of inspiration for this framework. Nonetheless, Starlite is not FastAPI - it
has a different design, different project goals and a completely different codebase.

1. The goal of this project is to become a community driven project. That is, not to have a single "owner" but rather a
   core team of maintainers that leads the project, as well as community contributors.
2. Starlite draws inspiration from NestJS - a contemporary TypeScript framework - which places opinions and patterns at
   its core. As such, the design of the API breaks from the Starlette design and instead offers an opinionated
   alternative.
3. Finally, Python OOP is extremely powerful and versatile. While still allowing for function based endpoints, Starlite
   seeks to build on this by placing class based Controllers at its core.

### Features and roadmap

- [x] sync and async API endpoints
- [x] fast json serialization using [orjson](https://github.com/ijl/orjson)
- [x] class based controllers
- [x] decorators based configuration
- [x] rigorous typing and type inference
- [x] layered dependency injection
- [x] automatic OpenAPI schema generation
- [x] support for pydantic models and pydantic dataclasses
- [x] support for vanilla python dataclasses
- [x] extended testing support
- [x] built-in [Redoc](https://github.com/Redocly/redoc) based OpenAPI UI
- [x] route guards
- [ ] schemathesis integration

### Contributing

Starlite is open to contributions big and small. You can always [join our discord](https://discord.gg/X3FJqy8d2j) server
to discuss contributions and project maintenance. For guidelines on how to contribute, please
see [the contribution guide](CONTRIBUTING.md).
