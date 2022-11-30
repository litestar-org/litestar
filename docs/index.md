<!-- markdownlint-disable -->

#

<img alt="Starlite logo" src="./images/SVG/starlite-banner.svg" width="100%" height="auto">

<center>

![PyPI - License](https://img.shields.io/pypi/l/starlite?color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/starlite)

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
<br />
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
<br />
[![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)](https://discord.gg/X3FJqy8d2j)
[![Matrix](https://img.shields.io/badge/%5Bm%5D%20chat%20on%20Matrix-bridged-blue)](https://matrix.to/#/#starlitespace:matrix.org)
<br />
[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://itnext.io/introducing-starlite-3928adaa19ae)

</center>
<!-- markdownlint-restore -->

Starlite is a light, opinionated and flexible ASGI API framework built on top of **[pydantic](https://github.com/samuelcolvin/pydantic)**.

The Starlite framework supports **[plugins](usage/10-plugins/0-plugins-intro.md)**, ships
with **[dependency injection](usage/6-dependency-injection/0-dependency-injection-intro.md)**,
**[security primitives](usage/8-security/0-intro.md)**,
**[OpenAPI specifications-generation](usage/12-openapi/0-openapi-intro.md)**,
**[MessagePack](https://msgpack.org/)** support – among other common API-framework components such
as **[middleware](usage/7-middleware/0-middleware-intro.md)**.

## Installation

```shell
pip install starlite
```

??? "Extras"

    [Brotli Compression Middleware](usage/7-middleware/0-middleware-intro.md#brotli)
    :
        ```shell
        pip install starlite[brotli]
        ```

    [Client-side sessions](usage/7-middleware/3-builtin-middlewares/5-session-middleware.md#Client-side-sessions)
    :
        ```shell
        pip install starlite[cryptography]
        ```

    [Server-side sessions with redis / Redis caching](usage/7-middleware/3-builtin-middlewares/5-session-middleware/#redis-storage)
    :
        ```shell
        pip install starlite[redis]
        ```

    [Server-side sessions with memcached / memcached caching](usage/7-middleware/3-builtin-middlewares/5-session-middleware/#memcached-storage)
    :
        ```shell
        pip install starlite[memcached]
        ```

    [Picologging](usage/0-the-starlite-app/4-logging/#using-picologging)
    :
        ```shell
        pip install starlite[picologging]
        ```

    [StructLog](usage/0-the-starlite-app/4-logging/#using-structlog)
    :
        ```shell
        pip install starlite[structlog]
        ```

    [OpenTelemetry](usage/18-contrib/0-open-telemetry/)
    :
        ```shell
        pip install starlite[openetelemetry]
        ```

    All extras
    :
        ```shell
        pip install starlite[full]
        ```

## Minimal Example

**Define your data model** using pydantic or any library based on it (for example ormar, beanie, SQLModel):

```python title="my_app/models/user.py"
from pydantic import BaseModel, UUID4


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4
```

Alternatively, you can **use a dataclass** – either from dataclasses or from pydantic, or a [`TypedDict`][typing.TypedDict]:

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

**Define a Controller** for your data model:

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
    async def partial_update_user(self, user_id: UUID4, data: Partial[User]) -> User:
        ...

    @put(path="/{user_id:uuid}")
    async def update_user(self, user_id: UUID4, data: User) -> User:
        ...

    @get(path="/{user_id:uuid}")
    async def get_user(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id:uuid}")
    async def delete_user(self, user_id: UUID4) -> None:
        ...
```

When **instantiating** your app, **import your controller** into your application's entry-point and pass it to Starlite:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.controllers.user import UserController

app = Starlite(route_handlers=[UserController])
```

To **run your application**, use an ASGI server such as [uvicorn](https://www.uvicorn.org/):

```shell
uvicorn my_app.main:app --reload
```

## Example Applications

- [starlite-pg-redis-docker](https://github.com/starlite-api/starlite-pg-redis-docker): In addition to Starlite, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Starlite projects, this application is open to contributions, big and small.
- [starlite-hello-world](https://github.com/starlite-api/starlite-hello-world): A bare-minimum application setup. Great
  for testing and POC work.


## About the Starlite Project

Starlite is a high-level, opinionated framework, built with validation (on top of [pydantic](https://pydantic-docs.helpmanual.io/)) in mind.
The idea to build an ASGI framework that's deeply integrated with pydantic is of course not new - it was first done in FastAPI,
which in this regard (and some others) was a source of inspiration for this framework. Nonetheless, Starlite is not FastAPI -
it has a different design, different project goals and a completely different codebase.

1. The goal of this project is to be community-driven. That is, not to have a single author,
   but rather a core team of maintainers leading the project, as well as community contributors.
   Starlite currently has 5 maintainers and is being very actively developed.
2. Starlite draws **inspiration from NestJS** - a contemporary TypeScript framework - which places opinions and patterns
   at its core.
3. While still allowing for **function-based endpoints**, Starlite seeks to build on Python's powerful and versatile OOP,
   by placing **class-based controllers** at its core.
4. Starlite is **not** a microframework. Unlike frameworks such as FastAPI, Starlette or Flask, Starlite includes a lot of
   functionalities out of the box needed for a typical modern web application, such as ORM integration,
   client- and server-side sessions, caching, OpenTelemetry integration and many more. It's not aiming to be "the next Django"
   (for example, it will never feature its own ORM), but its scope is not micro either.


### Project Governance

From its inception, Starlite was envisaged as a community driven project. We encourage users to become involved with the
project - feel free to open issues, chime in on discussions, review pull requests and of course - contribute code.

The project is led by a group of maintainers. You can see the list of maintainers in the `pyproject.toml` file.
Additionally, substantial contributors are invited to be members of the `starlite-api` organization. Our aim is to
increase the number of maintainers and have at least 5 active maintainers - this will ensure the long term stability and
growth of Starlite in the long run. Contributors who show commitment, contribute great code and show a willingness to
become maintainers will be invited to do so. So really feel free to contribute and propose yourself as a maintainer once
you contribute substantially.


### Contribution Guide

Any and all contributions and involvement with the project is welcome. The easiest way to begin contributing
is to check out the open issues - and reach out on our discord server or Matrix space.

--8<-- "CONTRIBUTING.MD"


### License

--8<-- "LICENSE"
