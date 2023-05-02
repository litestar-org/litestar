<!-- markdownlint-disable -->
<p align="center">
  <img src="artwork/banner-light.svg#gh-light-mode-only" alt="Litestar Logo - Light" width="100%" height="auto" />
  <img src="artwork/banner-dark.svg#gh-dark-mode-only" alt="Litestar Logo - Dark" width="100%" height="auto" />
</p>
<!-- markdownlint-restore -->

<div align="center">

[![ci](https://github.com/litestar-org/litestar/actions/workflows/ci.yaml/badge.svg)](https://github.com/litestar-org/litestar/actions/workflows/ci.yaml)
[![PyPI - Version](https://badge.fury.io/py/litestar.svg)](https://badge.fury.io/py/litestar)
![PyPI - License](https://img.shields.io/pypi/l/litestar?color=blue)
![PyPI - Support Python Versions](https://img.shields.io/pypi/pyversions/litestar)

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=litestar-org_litestar&metric=coverage)](https://sonarcloud.io/summary/new_code?id=litestar-org_litestar)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=litestar-org_litestar&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=litestar-org_litestar)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=litestar-org_litestar&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=litestar-org_litestar)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=litestar-org_litestar&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=litestar-org_litestar)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=litestar-org_litestar&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=litestar-org_litestar)

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-99-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
<!-- prettier-ignore-end -->

[![Reddit](https://img.shields.io/reddit/subreddit-subscribers/litestarapi?label=r%2FLitestar&logo=reddit)](https://reddit.com/r/litestarapi)
[![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)](https://discord.gg/X3FJqy8d2j)
[![Matrix](https://img.shields.io/badge/%5Bm%5D%20chat%20on%20Matrix-bridged-blue)](https://matrix.to/#/#litestar:matrix.org)
[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://blog.litestar.dev)

</div>

# Starlite → Litestar

**[Starlite has been renamed to Litestar](https://litestar.dev/about/organization.html#litestar-and-starlite)**

<hr>

Litestar is a powerful, performant, flexible and opinionated ASGI framework,
offering first class typing support and a full [Pydantic](https://github.com/pydantic/pydantic)
integration.

Check out the [documentation 📚](https://docs.litestar.dev/).

## Installation

```shell
pip install litestar
```

**Litestar 2.0 is coming out soon**, bringing many new features and improvements.
You can check out the alpha version by instead running

```shell
pip install litestar==2.0.0alpha3
```

## Quick Start

```python
from litestar import Litestar, get


@get("/")
def hello_world() -> dict[str, str]:
    """Keeping the tradition alive with hello world."""
    return {"hello": "world"}


app = Litestar(route_handlers=[hello_world])
```

## Core Features

- [Class based controllers](#class-based-controllers)
- [Dependency Injection](#dependency-injection)
- [Validation and Parsing](#data-parsing-type-hints-and-pydantic) using [Pydantic](https://github.com/pydantic/pydantic)
- [Layered Middleware](#middleware)
- [Plugin System](#plugin-system-orm-support-and-dtos)
- [OpenAPI 3.1 schema generation](#openapi)
- [Life Cycle Hooks](#request-life-cycle-hooks)
- [Route Guards based Authorization](#route-guards)
- Layered Parameter declaration
- SQLAlchemy Support (via plugin)
- Piccolo ORM Support (via plugin)
- Tortoise ORM Support (via plugin)
- Extended testing support
- [Automatic API documentation with](#redoc-swagger-ui-and-stoplight-elements-api-documentation):
  - [Redoc](https://github.com/Redocly/redoc)
  - [Stoplight Elements](https://github.com/stoplightio/elements)
  - [Swagger-UI](https://swagger.io/tools/swagger-ui/)
- Support for dataclasses and `TypedDict`
- [Trio](https://trio.readthedocs.io/en/stable/) support (built-in, via [AnyIO](https://anyio.readthedocs.io/))
- Ultra-fast json serialization and deserialization using [msgspec](https://github.com/jcrist/msgspec)

## Example Applications

- [starlite-pg-redis-docker](https://github.com/litestar-org/starlite-pg-redis-docker): In addition to Litestar, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Litestar projects, this application is open to contributions, big and small.
- [litestar-hello-world](https://github.com/litestar-org/litestar-hello-world): A bare-minimum application setup. Great
  for testing and POC work.

## Performance

Litestar is fast. It is on par with, or significantly faster than comparable ASGI frameworks.

You can see and run the benchmarks [here](https://github.com/litestar-org/api-performance-tests),
or read more about it [here](https://docs.litestar.dev/latest/benchmarks) in our documentation.

### JSON Benchmarks

![JSON benchmarks](docs/images/benchmarks/rps_json.svg)

### Plaintext Benchmarks

![Plaintext benchmarks](docs/images/benchmarks/rps_plaintext.svg)

## Features

### Class Based Controllers

While supporting function based route handlers, Litestar also supports and promotes python OOP using class based
controllers:

```python title="my_app/controllers/user.py"
from typing import List, Optional

from pydantic import UUID4
from litestar import Controller, get, post, put, patch, delete
from litestar.partial import Partial
from datetime import datetime

from my_app.models import User


class UserController(Controller):
    path = "/users"

    @post()
    async def create_user(self, data: User) -> User:
        ...

    @get()
    async def list_users(self) -> List[User]:
        ...

    @get(path="/{date:int}")
    async def list_new_users(self, date: datetime) -> List[User]:
        ...

    @patch(path="/{user_id:uuid}")
    async def partial_update_user(self, user_id: UUID4, data: Partial[User]) -> User:
        ...

    @put(path="/{user_id:uuid}")
    async def update_user(self, user_id: UUID4, data: User) -> User:
        ...

    @get(path="/{user_name:str}")
    async def get_user_by_name(self, user_name: str) -> Optional[User]:
        ...

    @get(path="/{user_id:uuid}")
    async def get_user(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id:uuid}")
    async def delete_user(self, user_id: UUID4) -> None:
        ...
```

### Data Parsing, Type Hints and Pydantic

Litestar is rigorously typed, and it enforces typing. For example, if you forget to type a return value for a route
handler, an exception will be raised. The reason for this is that Litestar uses typing data to generate OpenAPI specs,
as well as to validate and parse data. Thus typing is absolutely essential to the framework.

Furthermore, Litestar allows extending its support using plugins.

### Plugin System, ORM support and DTOs

Litestar has a plugin system that allows the user to extend serialization/deserialization, OpenAPI generation and other
features. It ships with a builtin plugin for SQL Alchemy, which allows the user to use SQLAlchemy declarative classes
"natively", i.e. as type parameters that will be serialized/deserialized and to return them as values from route
handlers.

Litestar also supports the programmatic creation of DTOs with a `DTOFactory` class, which also supports the use of
plugins.

### OpenAPI

Litestar has custom logic to generate OpenAPI 3.1.0 schema, include optional generation of examples using the
`pydantic-factories` library.

#### ReDoc, Swagger-UI and Stoplight Elements API Documentation

Litestar serves the documentation from the generated OpenAPI schema with:

- [ReDoc](https://redoc.ly/)
- [Swagger-UI](https://swagger.io/tools/swagger-ui/)
- [Stoplight Elements](https://github.com/stoplightio/elements)

All these are available and enabled by default.

### Dependency Injection

Litestar has a simple but powerful DI system inspired by pytest. You can define named dependencies - sync or async - at
different levels of the application, and then selective use or overwrite them.

```python
from litestar import Litestar, get
from litestar.di import Provide


async def my_dependency() -> str:
    ...


@get("/")
async def index(injected: str) -> str:
    return injected


app = Litestar([index], dependencies={"injected": Provide(my_dependency)})
```

### Middleware

Litestar supports typical ASGI middleware and ships with middlewares to handle things such as

- CORS
- CSRF
- Rate limiting
- GZip and Brotli compression
- Client- and server-side sessions

### Route Guards

Litestar has an authorization mechanism called `guards`, which allows the user to define guard functions at different
level of the application (app, router, controller etc.) and validate the request before hitting the route handler
function.

```python
from litestar import Litestar, get

from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.exceptions import NotAuthorizedException


async def is_authorized(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    # validate authorization
    # if not authorized, raise NotAuthorizedException
    raise NotAuthorizedException()


@get("/", guards=[is_authorized])
async def index() -> None:
    ...


app = Litestar([index])
```

### Request Life Cycle Hooks

Litestar supports request life cycle hooks, similarly to Flask - i.e. `before_request` and `after_request`

## Contributing

Litestar is open to contributions big and small. You can always [join our discord](https://discord.gg/X3FJqy8d2j) server
or [join our Matrix](https://matrix.to/#/#litestar:matrix.org) space
to discuss contributions and project maintenance. For guidelines on how to contribute, please
see [the contribution guide](CONTRIBUTING.rst).

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/nhirschfeld/"><img src="https://avatars.githubusercontent.com/u/30733348?v=4?s=100" width="100px;" alt="Na'aman Hirschfeld"/><br /><sub><b>Na'aman Hirschfeld</b></sub></a><br /><a href="#maintenance-Goldziher" title="Maintenance">🚧</a> <a href="https://github.com/litestar-org/litestar/commits?author=Goldziher" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=Goldziher" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=Goldziher" title="Tests">⚠️</a> <a href="#ideas-Goldziher" title="Ideas, Planning, & Feedback">🤔</a> <a href="#example-Goldziher" title="Examples">💡</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3AGoldziher" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/peterschutt"><img src="https://avatars.githubusercontent.com/u/20659309?v=4?s=100" width="100px;" alt="Peter Schutt"/><br /><sub><b>Peter Schutt</b></sub></a><br /><a href="#maintenance-peterschutt" title="Maintenance">🚧</a> <a href="https://github.com/litestar-org/litestar/commits?author=peterschutt" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=peterschutt" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=peterschutt" title="Tests">⚠️</a> <a href="#ideas-peterschutt" title="Ideas, Planning, & Feedback">🤔</a> <a href="#example-peterschutt" title="Examples">💡</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3Apeterschutt" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://ashwinvin.github.io"><img src="https://avatars.githubusercontent.com/u/38067089?v=4?s=100" width="100px;" alt="Ashwin Vinod"/><br /><sub><b>Ashwin Vinod</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ashwinvin" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=ashwinvin" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.damiankress.de"><img src="https://avatars.githubusercontent.com/u/28515387?v=4?s=100" width="100px;" alt="Damian"/><br /><sub><b>Damian</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=dkress59" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://remotepixel.ca"><img src="https://avatars.githubusercontent.com/u/10407788?v=4?s=100" width="100px;" alt="Vincent Sarago"/><br /><sub><b>Vincent Sarago</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=vincentsarago" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://hotfix.guru"><img src="https://avatars.githubusercontent.com/u/5310116?v=4?s=100" width="100px;" alt="Jonas Krüger Svensson"/><br /><sub><b>Jonas Krüger Svensson</b></sub></a><br /><a href="#platform-JonasKs" title="Packaging/porting to new platform">📦</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sondrelg"><img src="https://avatars.githubusercontent.com/u/25310870?v=4?s=100" width="100px;" alt="Sondre Lillebø Gundersen"/><br /><sub><b>Sondre Lillebø Gundersen</b></sub></a><br /><a href="#platform-sondrelg" title="Packaging/porting to new platform">📦</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/vrslev"><img src="https://avatars.githubusercontent.com/u/75225148?v=4?s=100" width="100px;" alt="Lev"/><br /><sub><b>Lev</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=vrslev" title="Code">💻</a> <a href="#ideas-vrslev" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/timwedde"><img src="https://avatars.githubusercontent.com/u/20231751?v=4?s=100" width="100px;" alt="Tim Wedde"/><br /><sub><b>Tim Wedde</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=timwedde" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tclasen"><img src="https://avatars.githubusercontent.com/u/11999013?v=4?s=100" width="100px;" alt="Tory Clasen"/><br /><sub><b>Tory Clasen</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=tclasen" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://t.me/Bobronium"><img src="https://avatars.githubusercontent.com/u/36469655?v=4?s=100" width="100px;" alt="Arseny Boykov"/><br /><sub><b>Arseny Boykov</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Bobronium" title="Code">💻</a> <a href="#ideas-Bobronium" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/yudjinn"><img src="https://avatars.githubusercontent.com/u/7493084?v=4?s=100" width="100px;" alt="Jacob Rodgers"/><br /><sub><b>Jacob Rodgers</b></sub></a><br /><a href="#example-yudjinn" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/danesolberg"><img src="https://avatars.githubusercontent.com/u/25882507?v=4?s=100" width="100px;" alt="Dane Solberg"/><br /><sub><b>Dane Solberg</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=danesolberg" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/madlad33"><img src="https://avatars.githubusercontent.com/u/54079440?v=4?s=100" width="100px;" alt="madlad33"/><br /><sub><b>madlad33</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=madlad33" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://matthewtyleraylward.com"><img src="https://avatars.githubusercontent.com/u/19205392?v=4?s=100" width="100px;" alt="Matthew Aylward "/><br /><sub><b>Matthew Aylward </b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Butch78" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Joko013"><img src="https://avatars.githubusercontent.com/u/30841710?v=4?s=100" width="100px;" alt="Jan Klima"/><br /><sub><b>Jan Klima</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Joko013" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/i404788"><img src="https://avatars.githubusercontent.com/u/50617709?v=4?s=100" width="100px;" alt="C2D"/><br /><sub><b>C2D</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=i404788" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/to-ph"><img src="https://avatars.githubusercontent.com/u/84818322?v=4?s=100" width="100px;" alt="to-ph"/><br /><sub><b>to-ph</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=to-ph" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://imbev.gitlab.io/site"><img src="https://avatars.githubusercontent.com/u/105524473?v=4?s=100" width="100px;" alt="imbev"/><br /><sub><b>imbev</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=imbev" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://git.roboces.dev/catalin"><img src="https://avatars.githubusercontent.com/u/45485069?v=4?s=100" width="100px;" alt="cătălin"/><br /><sub><b>cătălin</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=185504a9" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Seon82"><img src="https://avatars.githubusercontent.com/u/46298009?v=4?s=100" width="100px;" alt="Seon82"/><br /><sub><b>Seon82</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Seon82" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/slavugan"><img src="https://avatars.githubusercontent.com/u/8457612?v=4?s=100" width="100px;" alt="Slava"/><br /><sub><b>Slava</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=slavugan" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Harry-Lees"><img src="https://avatars.githubusercontent.com/u/52263746?v=4?s=100" width="100px;" alt="Harry"/><br /><sub><b>Harry</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Harry-Lees" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=Harry-Lees" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cofin"><img src="https://avatars.githubusercontent.com/u/204685?v=4?s=100" width="100px;" alt="Cody Fincher"/><br /><sub><b>Cody Fincher</b></sub></a><br /><a href="#maintenance-cofin" title="Maintenance">🚧</a> <a href="https://github.com/litestar-org/litestar/commits?author=cofin" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=cofin" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=cofin" title="Tests">⚠️</a> <a href="#ideas-cofin" title="Ideas, Planning, & Feedback">🤔</a> <a href="#example-cofin" title="Examples">💡</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3Acofin" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.patreon.com/cclauss"><img src="https://avatars.githubusercontent.com/u/3709715?v=4?s=100" width="100px;" alt="Christian Clauss"/><br /><sub><b>Christian Clauss</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=cclauss" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/josepdaniel"><img src="https://avatars.githubusercontent.com/u/36941460?v=4?s=100" width="100px;" alt="josepdaniel"/><br /><sub><b>josepdaniel</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=josepdaniel" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/devtud"><img src="https://avatars.githubusercontent.com/u/6808024?v=4?s=100" width="100px;" alt="devtud"/><br /><sub><b>devtud</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/issues?q=author%3Adevtud" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/nramos0"><img src="https://avatars.githubusercontent.com/u/35410160?v=4?s=100" width="100px;" alt="Nicholas Ramos"/><br /><sub><b>Nicholas Ramos</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=nramos0" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://twitter.com/seladb"><img src="https://avatars.githubusercontent.com/u/9059541?v=4?s=100" width="100px;" alt="seladb"/><br /><sub><b>seladb</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=seladb" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=seladb" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/aedify-swi"><img src="https://avatars.githubusercontent.com/u/66629131?v=4?s=100" width="100px;" alt="Simon Wienhöfer"/><br /><sub><b>Simon Wienhöfer</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=aedify-swi" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mobiusxs"><img src="https://avatars.githubusercontent.com/u/57055149?v=4?s=100" width="100px;" alt="MobiusXS"/><br /><sub><b>MobiusXS</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=mobiusxs" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://aidansimard.dev"><img src="https://avatars.githubusercontent.com/u/73361895?v=4?s=100" width="100px;" alt="Aidan Simard"/><br /><sub><b>Aidan Simard</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Aidan-Simard" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/waweber"><img src="https://avatars.githubusercontent.com/u/714224?v=4?s=100" width="100px;" alt="wweber"/><br /><sub><b>wweber</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=waweber" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://scolvin.com"><img src="https://avatars.githubusercontent.com/u/4039449?v=4?s=100" width="100px;" alt="Samuel Colvin"/><br /><sub><b>Samuel Colvin</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=samuelcolvin" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/toudi"><img src="https://avatars.githubusercontent.com/u/81148?v=4?s=100" width="100px;" alt="Mateusz Mikołajczyk"/><br /><sub><b>Mateusz Mikołajczyk</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=toudi" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Alex-CodeLab"><img src="https://avatars.githubusercontent.com/u/1678423?v=4?s=100" width="100px;" alt="Alex "/><br /><sub><b>Alex </b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Alex-CodeLab" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/odiseo0"><img src="https://avatars.githubusercontent.com/u/87550035?v=4?s=100" width="100px;" alt="Odiseo"/><br /><sub><b>Odiseo</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=odiseo0" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ingjavierpinilla"><img src="https://avatars.githubusercontent.com/u/36714646?v=4?s=100" width="100px;" alt="Javier  Pinilla"/><br /><sub><b>Javier  Pinilla</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ingjavierpinilla" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Chaoyingz"><img src="https://avatars.githubusercontent.com/u/32626585?v=4?s=100" width="100px;" alt="Chaoying"/><br /><sub><b>Chaoying</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Chaoyingz" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/infohash"><img src="https://avatars.githubusercontent.com/u/46137868?v=4?s=100" width="100px;" alt="infohash"/><br /><sub><b>infohash</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=infohash" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/john-ingles/"><img src="https://avatars.githubusercontent.com/u/35442886?v=4?s=100" width="100px;" alt="John Ingles"/><br /><sub><b>John Ingles</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=john-ingles" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/h0rn3t"><img src="https://avatars.githubusercontent.com/u/1213719?v=4?s=100" width="100px;" alt="Eugene"/><br /><sub><b>Eugene</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=h0rn3t" title="Tests">⚠️</a> <a href="https://github.com/litestar-org/litestar/commits?author=h0rn3t" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jonadaly"><img src="https://avatars.githubusercontent.com/u/26462826?v=4?s=100" width="100px;" alt="Jon Daly"/><br /><sub><b>Jon Daly</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=jonadaly" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=jonadaly" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://harshallaheri.me/"><img src="https://avatars.githubusercontent.com/u/73422191?v=4?s=100" width="100px;" alt="Harshal Laheri"/><br /><sub><b>Harshal Laheri</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Harshal6927" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=Harshal6927" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sorasful"><img src="https://avatars.githubusercontent.com/u/32820423?v=4?s=100" width="100px;" alt="Téva KRIEF"/><br /><sub><b>Téva KRIEF</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=sorasful" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jtraub"><img src="https://avatars.githubusercontent.com/u/153191?v=4?s=100" width="100px;" alt="Konstantin Mikhailov"/><br /><sub><b>Konstantin Mikhailov</b></sub></a><br /><a href="#maintenance-jtraub" title="Maintenance">🚧</a> <a href="https://github.com/litestar-org/litestar/commits?author=jtraub" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=jtraub" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=jtraub" title="Tests">⚠️</a> <a href="#ideas-jtraub" title="Ideas, Planning, & Feedback">🤔</a> <a href="#example-jtraub" title="Examples">💡</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3Ajtraub" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://linkedin.com/in/mitchell-henry334/"><img src="https://avatars.githubusercontent.com/u/17354727?v=4?s=100" width="100px;" alt="Mitchell Henry"/><br /><sub><b>Mitchell Henry</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=devmitch" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/chbndrhnns"><img src="https://avatars.githubusercontent.com/u/7534547?v=4?s=100" width="100px;" alt="chbndrhnns"/><br /><sub><b>chbndrhnns</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=chbndrhnns" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/nielsvanhooy"><img src="https://avatars.githubusercontent.com/u/40770348?v=4?s=100" width="100px;" alt="nielsvanhooy"/><br /><sub><b>nielsvanhooy</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=nielsvanhooy" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/provinzkraut"><img src="https://avatars.githubusercontent.com/u/25355197?v=4?s=100" width="100px;" alt="provinzkraut"/><br /><sub><b>provinzkraut</b></sub></a><br /><a href="#maintenance-provinzkraut" title="Maintenance">🚧</a> <a href="https://github.com/litestar-org/litestar/commits?author=provinzkraut" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=provinzkraut" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=provinzkraut" title="Tests">⚠️</a> <a href="#ideas-provinzkraut" title="Ideas, Planning, & Feedback">🤔</a> <a href="#example-provinzkraut" title="Examples">💡</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3Aprovinzkraut" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jab"><img src="https://avatars.githubusercontent.com/u/64992?v=4?s=100" width="100px;" alt="Joshua Bronson"/><br /><sub><b>Joshua Bronson</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=jab" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://linkedin.com/in/roman-reznikov"><img src="https://avatars.githubusercontent.com/u/44291988?v=4?s=100" width="100px;" alt="Roman Reznikov"/><br /><sub><b>Roman Reznikov</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ReznikovRoman" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://mookrs.com"><img src="https://avatars.githubusercontent.com/u/985439?v=4?s=100" width="100px;" alt="mookrs"/><br /><sub><b>mookrs</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=mookrs" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://mike.depalatis.net"><img src="https://avatars.githubusercontent.com/u/2805515?v=4?s=100" width="100px;" alt="Mike DePalatis"/><br /><sub><b>Mike DePalatis</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=mivade" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pemocarlo"><img src="https://avatars.githubusercontent.com/u/7297323?v=4?s=100" width="100px;" alt="Carlos Alberto Pérez-Molano"/><br /><sub><b>Carlos Alberto Pérez-Molano</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=pemocarlo" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.bestcryptocodes.com"><img src="https://avatars.githubusercontent.com/u/114229148?v=4?s=100" width="100px;" alt="ThinksFast"/><br /><sub><b>ThinksFast</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ThinksFast" title="Tests">⚠️</a> <a href="https://github.com/litestar-org/litestar/commits?author=ThinksFast" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ottermata"><img src="https://avatars.githubusercontent.com/u/9451844?v=4?s=100" width="100px;" alt="Christopher Krause"/><br /><sub><b>Christopher Krause</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ottermata" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.kylesmith.me"><img src="https://avatars.githubusercontent.com/u/1161424?v=4?s=100" width="100px;" alt="Kyle Smith"/><br /><sub><b>Kyle Smith</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=smithk86" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=smithk86" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/issues?q=author%3Asmithk86" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/scott2b"><img src="https://avatars.githubusercontent.com/u/307713?v=4?s=100" width="100px;" alt="Scott Bradley"/><br /><sub><b>Scott Bradley</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/issues?q=author%3Ascott2b" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/srikanthccv/"><img src="https://avatars.githubusercontent.com/u/22846633?v=4?s=100" width="100px;" alt="Srikanth Chekuri"/><br /><sub><b>Srikanth Chekuri</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=srikanthccv" title="Tests">⚠️</a> <a href="https://github.com/litestar-org/litestar/commits?author=srikanthccv" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://lonelyviking.com"><img src="https://avatars.githubusercontent.com/u/78952809?v=4?s=100" width="100px;" alt="Michael Bosch"/><br /><sub><b>Michael Bosch</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=LonelyVikingMichael" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sssssss340"><img src="https://avatars.githubusercontent.com/u/8406195?v=4?s=100" width="100px;" alt="sssssss340"/><br /><sub><b>sssssss340</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/issues?q=author%3Asssssss340" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ste-pool"><img src="https://avatars.githubusercontent.com/u/17198460?v=4?s=100" width="100px;" alt="ste-pool"/><br /><sub><b>ste-pool</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ste-pool" title="Code">💻</a> <a href="#infra-ste-pool" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Alc-Alc"><img src="https://avatars.githubusercontent.com/u/45509143?v=4?s=100" width="100px;" alt="Alc-Alc"/><br /><sub><b>Alc-Alc</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Alc-Alc" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=Alc-Alc" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://asomethings.com"><img src="https://avatars.githubusercontent.com/u/16171942?v=4?s=100" width="100px;" alt="asomethings"/><br /><sub><b>asomethings</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=asomethings" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/garburator"><img src="https://avatars.githubusercontent.com/u/14207857?v=4?s=100" width="100px;" alt="Garry Bullock"/><br /><sub><b>Garry Bullock</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=garburator" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/NiclasHaderer"><img src="https://avatars.githubusercontent.com/u/109728711?v=4?s=100" width="100px;" alt="Niclas Haderer"/><br /><sub><b>Niclas Haderer</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=NiclasHaderer" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dialvarezs"><img src="https://avatars.githubusercontent.com/u/13831919?v=4?s=100" width="100px;" alt="Diego Alvarez"/><br /><sub><b>Diego Alvarez</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=dialvarezs" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=dialvarezs" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.rgare.com"><img src="https://avatars.githubusercontent.com/u/51208317?v=4?s=100" width="100px;" alt="Jason Nance"/><br /><sub><b>Jason Nance</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=rgajason" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/spikenn"><img src="https://avatars.githubusercontent.com/u/32995595?v=4?s=100" width="100px;" alt="Igor Kapadze"/><br /><sub><b>Igor Kapadze</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=spikenn" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://jarmos.vercel.app"><img src="https://avatars.githubusercontent.com/u/31373860?v=4?s=100" width="100px;" alt="Somraj Saha"/><br /><sub><b>Somraj Saha</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Jarmos-san" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://skulason.me"><img src="https://avatars.githubusercontent.com/u/11139514?v=4?s=100" width="100px;" alt="Magnús Ágúst Skúlason"/><br /><sub><b>Magnús Ágúst Skúlason</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=maggias" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=maggias" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://alessioparma.xyz/"><img src="https://avatars.githubusercontent.com/u/4697032?v=4?s=100" width="100px;" alt="Alessio Parma"/><br /><sub><b>Alessio Parma</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=pomma89" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Lugoues"><img src="https://avatars.githubusercontent.com/u/372610?v=4?s=100" width="100px;" alt="Peter Brunner"/><br /><sub><b>Peter Brunner</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Lugoues" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://scriptr.dev/"><img src="https://avatars.githubusercontent.com/u/45884264?v=4?s=100" width="100px;" alt="Jacob Coffee"/><br /><sub><b>Jacob Coffee</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=JacobCoffee" title="Documentation">📖</a> <a href="https://github.com/litestar-org/litestar/commits?author=JacobCoffee" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=JacobCoffee" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Gamazic"><img src="https://avatars.githubusercontent.com/u/33692402?v=4?s=100" width="100px;" alt="Gamazic"/><br /><sub><b>Gamazic</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Gamazic" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/kareemmahlees"><img src="https://avatars.githubusercontent.com/u/89863279?v=4?s=100" width="100px;" alt="Kareem Mahlees"/><br /><sub><b>Kareem Mahlees</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=kareemmahlees" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/abdulhaq-e"><img src="https://avatars.githubusercontent.com/u/2532125?v=4?s=100" width="100px;" alt="Abdulhaq Emhemmed"/><br /><sub><b>Abdulhaq Emhemmed</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=abdulhaq-e" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jenish2014"><img src="https://avatars.githubusercontent.com/u/9599888?v=4?s=100" width="100px;" alt="Jenish"/><br /><sub><b>Jenish</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=jenish2014" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=jenish2014" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/chris-telemetry"><img src="https://avatars.githubusercontent.com/u/78052999?v=4?s=100" width="100px;" alt="chris-telemetry"/><br /><sub><b>chris-telemetry</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=chris-telemetry" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://wardpearce.com"><img src="https://avatars.githubusercontent.com/u/27844174?v=4?s=100" width="100px;" alt="Ward"/><br /><sub><b>Ward</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/issues?q=author%3AWardPearce" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://knowsuchagency.com"><img src="https://avatars.githubusercontent.com/u/11974795?v=4?s=100" width="100px;" alt="Stephan Fitzpatrick"/><br /><sub><b>Stephan Fitzpatrick</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/issues?q=author%3Aknowsuchagency" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://codepen.io/ekeric13/"><img src="https://avatars.githubusercontent.com/u/6489651?v=4?s=100" width="100px;" alt="Eric Kennedy"/><br /><sub><b>Eric Kennedy</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=ekeric13" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/wassafshahzad"><img src="https://avatars.githubusercontent.com/u/25094157?v=4?s=100" width="100px;" alt="wassaf shahzad"/><br /><sub><b>wassaf shahzad</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=wassafshahzad" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://nilsso.github.io"><img src="https://avatars.githubusercontent.com/u/567181?v=4?s=100" width="100px;" alt="Nils Olsson"/><br /><sub><b>Nils Olsson</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=nilsso" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://rileychase.net"><img src="https://avatars.githubusercontent.com/u/1491530?v=4?s=100" width="100px;" alt="Riley Chase"/><br /><sub><b>Riley Chase</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Nadock" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://gh.arielle.codes"><img src="https://avatars.githubusercontent.com/u/71233171?v=4?s=100" width="100px;" alt="arl"/><br /><sub><b>arl</b></sub></a><br /><a href="#maintenance-onerandomusername" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Galdanwing"><img src="https://avatars.githubusercontent.com/u/29492757?v=4?s=100" width="100px;" alt="Antoine van der Horst"/><br /><sub><b>Antoine van der Horst</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=Galdanwing" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://nick.groenen.me"><img src="https://avatars.githubusercontent.com/u/145285?v=4?s=100" width="100px;" alt="Nick Groenen"/><br /><sub><b>Nick Groenen</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=zoni" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/giorgiovilardo"><img src="https://avatars.githubusercontent.com/u/56472600?v=4?s=100" width="100px;" alt="Giorgio Vilardo"/><br /><sub><b>Giorgio Vilardo</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=giorgiovilardo" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bollwyvl"><img src="https://avatars.githubusercontent.com/u/45380?v=4?s=100" width="100px;" alt="Nicholas Bollweg"/><br /><sub><b>Nicholas Bollweg</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=bollwyvl" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tompin82"><img src="https://avatars.githubusercontent.com/u/47041409?v=4?s=100" width="100px;" alt="Tomas Jonsson"/><br /><sub><b>Tomas Jonsson</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=tompin82" title="Tests">⚠️</a> <a href="https://github.com/litestar-org/litestar/commits?author=tompin82" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/khiem-doan/"><img src="https://avatars.githubusercontent.com/u/15646249?v=4?s=100" width="100px;" alt="Khiem Doan"/><br /><sub><b>Khiem Doan</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=khiemdoan" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/kedod"><img src="https://avatars.githubusercontent.com/u/35638715?v=4?s=100" width="100px;" alt="kedod"/><br /><sub><b>kedod</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=kedod" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sonpro1296"><img src="https://avatars.githubusercontent.com/u/17319142?v=4?s=100" width="100px;" alt="sonpro1296"/><br /><sub><b>sonpro1296</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=sonpro1296" title="Code">💻</a> <a href="https://github.com/litestar-org/litestar/commits?author=sonpro1296" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://patrickarmengol.com"><img src="https://avatars.githubusercontent.com/u/42473149?v=4?s=100" width="100px;" alt="Patrick Armengol"/><br /><sub><b>Patrick Armengol</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=patrickarmengol" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://sanderwegter.nl"><img src="https://avatars.githubusercontent.com/u/7465799?v=4?s=100" width="100px;" alt="Sander"/><br /><sub><b>Sander</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=SanderWegter" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/erhuabushuo"><img src="https://avatars.githubusercontent.com/u/1642364?v=4?s=100" width="100px;" alt="疯人院主任"/><br /><sub><b>疯人院主任</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=erhuabushuo" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/aviral-nayya"><img src="https://avatars.githubusercontent.com/u/121891493?v=4?s=100" width="100px;" alt="aviral-nayya"/><br /><sub><b>aviral-nayya</b></sub></a><br /><a href="https://github.com/litestar-org/litestar/commits?author=aviral-nayya" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification.
Contributions of any kind welcome!
