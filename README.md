<img alt="StarLite logo" src="./starlite-logo.svg" width=100%, height="auto">

![PyPI - License](https://img.shields.io/pypi/l/starlite?color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/starlite)
![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=bugs)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Goldziher_starlite&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Goldziher_starlite)

# StarLite

StarLite is a flexible, extensible and opinionated ASGI API framework built on top of pydantic and Starlette.

Features and roadmap:

- [x] sync and async API endpoints
- [x] class based controllers
- [x] decorators based configuration
- [x] rigorous typing and type inference
- [x] layered dependency injection
- [x] automatic OpenAPI schema generation
- [x] support for pydantic models and pydantic dataclasses
- [x] support for vanilla python dataclasses
- [x] extended testing support
- [ ] request interceptors
- [ ] route guards
- [ ] schemathesis integration

## Example: Controller Pattern

Starlite supports class API components called "Controllers". Controllers are meant to group logical subcomponents, for
example - consider the following `UserController`:

```python3
from pydantic import BaseModel, UUID4
from starlite import Starlite
from starlite.controller import Controller
from starlite.handlers import get, post, put, patch, delete
from starlite.types import Partial


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4


class UserController(Controller):
    path = "/users"

    @post()
    async def create(self, data: User) -> User:
        ...

    @get()
    async def get_users(self) -> list[User]:
        ...

    @patch()
    async def partial_update_user(self, data: Partial[User]) -> User:
        ...

    @put()
    async def bulk_update_users(self, data: list[User]) -> list[User]:
        ...

    @get(path="/{user_id}")
    async def get_user_by_id(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id}")
    async def delete_user_by_id(self, user_id: UUID4) -> User:
        ...


app = Starlite(route_handlers=[UserController])

```
