<!-- markdownlint-disable -->
<img alt="Starlite logo" src="./docs/images/SVG/starlite-banner.svg" width="100%" height="auto">
<!-- markdownlint-restore -->

<div align="center">

![PyPI - License](https://img.shields.io/pypi/l/starlite?color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/starlite)

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=starlite-api_starlite&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=starlite-api_starlite)

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/starlite-api/starlite.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/starlite-api/starlite/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/starlite-api/starlite.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/starlite-api/starlite/alerts/)

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-49-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
<!-- prettier-ignore-end -->

[![Discord](https://img.shields.io/discord/919193495116337154?color=blue&label=chat%20on%20discord&logo=discord)](https://discord.gg/X3FJqy8d2j)
[![Matrix](https://img.shields.io/badge/%5Bm%5D%20chat%20on%20Matrix-bridged-blue)](https://matrix.to/#/#starlitespace:matrix.org)

[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://itnext.io/introducing-starlite-3928adaa19ae)

</div>

# Starlite

Starlite is a powerful, flexible and highly performant ASGI API framework built on top
of [Starlette](https://github.com/encode/starlette)
and [pydantic](https://github.com/samuelcolvin/pydantic).

Check out the [Starlite documentation 📚](https://starlite-api.github.io/starlite/)

## Installation

```shell
pip install starlite
```

## Quick Start

```python
from starlite import Starlite, get


@get("/")
def hello_world() -> dict[str, str]:
    """Keeping the tradition alive with hello world."""
    return {"hello": "world"}


app = Starlite(route_handlers=[hello_world])
```

## Core Features

- Both functional and OOP python support
- Class based controllers
- Extended testing support
- Builtin Validation and Parsing using Pydantic
- Dataclass Support
- Dependency Injection
- Layered Middleware
- Layered Parameter declaration
- Route Guards based Authorization
- Life Cycle Hooks
- Plugin System
- SQLAlchemy Support (via plugin)
- Tortoise-ORM Support (via plugin)
- Automatic OpenAPI 3.1 schema generation
- Support for [Redoc](https://github.com/Redocly/redoc)
- Support for [Swagger-UI](https://swagger.io/tools/swagger-ui/)
- Support for [Stoplight Elements](https://github.com/stoplightio/elements)
- Ultra-fast json serialization and deserialization using [orjson](https://github.com/ijl/orjson)

## Example Applications

- [starlite-pg-redis-docker](https://github.com/starlite-api/starlite-pg-redis-docker): In addition to Starlite, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Starlite projects, this application is open to contributions, big and small.
- [starlite-hello-world](https://github.com/starlite-api/starlite-hello-world): A bare-minimum application setup. Great
  for testing and POC work.

## Relation to Starlette and FastAPI

Although Starlite uses the Starlette ASGI toolkit, it does not simply extend Starlette, as FastAPI does. Starlite uses
selective pieces of Starlette while implementing its own routing and parsing logic, the primary reason for this is to
enforce a set of best practices and discourage misuse. This is done to promote simplicity and scalability - Starlite is
simple to use, easy to learn, and unlike both Starlette and FastAPI - it keeps complexity low when scaling.

### Performant

Additionally, Starlite is very fast in comparison to other ASGI
frameworks. In fact, the only framework that is faster
in [our benchmarks](https://github.com/starlite-api/api-performance-tests) is _BlackSheep_, which is almost completely
written in cython and does not work with pydantic out of the box as such:

#### JSON Benchmarks

<img alt="API JSON Benchmarks" src="https://github.com/starlite-api/api-performance-tests/raw/main/result-json.png">

#### PlainText Benchmarks

<img alt="API Plaintext Benchmarks" src="https://github.com/starlite-api/api-performance-tests/raw/main/result-plaintext.png">

Legend:

- a-: async, s-: sync
- np: no params, pp: path param, qp: query param, mp: mixed params

You can see and run the benchmarks [here](https://github.com/starlite-api/api-performance-tests).

### Class Based Controllers

While supporting function based route handlers, Starlite also supports and promotes python OOP using class based
controllers:

```python title="my_app/controllers/user.py"
from typing import List, Optional, NoReturn

from pydantic import UUID4
from starlite import Controller, Partial, get, post, put, patch, delete
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
    async def delete_user(self, user_id: UUID4) -> NoReturn:
        ...
```

### ReDoc, Swagger-UI and Stoplight Elements API Documentation

While running Starlite, you can view the generated OpenAPI documentation using a [ReDoc](https://redoc.ly/) site,
a [Swagger-UI](https://swagger.io/tools/swagger-ui/) as well as
a [Stoplight Elements](https://github.com/stoplightio/elements) site.

### Data Parsing, Type Hints and Pydantic

One key difference between Starlite and Starlette/FastAPI is in parsing of form data and query parameters- Starlite
supports mixed form data and has faster and better query parameter parsing.

Starlite is rigorously typed, and it enforces typing. For example, if you forget to type a return value for a route
handler, an exception will be raised. The reason for this is that Starlite uses typing data to generate OpenAPI specs,
as well as to validate and parse data. Thus typing is absolutely essential to the framework.

Furthermore, Starlite allows extending its support using plugins.

### SQLAlchemy Support, Plugin System and DTOs

Starlite has a plugin system that allows the user to extend serialization/deserialization, OpenAPI generation and other
features. It ships with a builtin plugin for SQL Alchemy, which allows the user to use SQLAlchemy declarative classes
"natively", i.e. as type parameters that will be serialized/deserialized and to return them as values from route
handlers.

Starlite also supports the programmatic creation of DTOs with a `DTOFactory` class, which also supports the use of
plugins.

### OpenAPI

Starlite has custom logic to generate OpenAPI 3.1.0 schema, the latest version. The schema generated by Starlite is
significantly more complete and more correct than those generated by FastAPI, and they include optional generation of
examples using the `pydantic-factories` library.

### Dependency Injection

Starlite has a simple but powerful DI system inspired by pytest. You can define named dependencies - sync or async - at
different levels of the application, and then selective use or overwrite them.

### Middleware

Starlite supports the Starlette Middleware system while simplifying it and offering builtin configuration of CORS and
some other middlewares.

### Route Guards

Starlite has an authorization mechanism called `guards`, which allows the user to define guard functions at different
level of the application (app, router, controller etc.) and validate the request before hitting the route handler
function.

### Request Life Cycle Hooks

Starlite supports request life cycle hooks, similarly to Flask - i.e. `before_request` and `after_request`

## Contributing

Starlite is open to contributions big and small. You can always [join our discord](https://discord.gg/X3FJqy8d2j) server
or [join our Matrix](https://matrix.to/#/#starlitespace:matrix.org) space
to discuss contributions and project maintenance. For guidelines on how to contribute, please
see [the contribution guide](CONTRIBUTING.md).

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center"><a href="https://www.linkedin.com/in/nhirschfeld/"><img src="https://avatars.githubusercontent.com/u/30733348?v=4?s=100" width="100px;" alt="Na'aman Hirschfeld"/><br /><sub><b>Na'aman Hirschfeld</b></sub></a><br /><a href="#maintenance-Goldziher" title="Maintenance">🚧</a> <a href="https://github.com/starlite-api/starlite/commits?author=Goldziher" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=Goldziher" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/peterschutt"><img src="https://avatars.githubusercontent.com/u/20659309?v=4?s=100" width="100px;" alt="Peter Schutt"/><br /><sub><b>Peter Schutt</b></sub></a><br /><a href="#maintenance-peterschutt" title="Maintenance">🚧</a> <a href="https://github.com/starlite-api/starlite/commits?author=peterschutt" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=peterschutt" title="Documentation">📖</a></td>
      <td align="center"><a href="https://ashwinvin.github.io"><img src="https://avatars.githubusercontent.com/u/38067089?v=4?s=100" width="100px;" alt="Ashwin Vinod"/><br /><sub><b>Ashwin Vinod</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=ashwinvin" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=ashwinvin" title="Documentation">📖</a></td>
      <td align="center"><a href="http://www.damiankress.de"><img src="https://avatars.githubusercontent.com/u/28515387?v=4?s=100" width="100px;" alt="Damian"/><br /><sub><b>Damian</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=dkress59" title="Documentation">📖</a></td>
      <td align="center"><a href="https://remotepixel.ca"><img src="https://avatars.githubusercontent.com/u/10407788?v=4?s=100" width="100px;" alt="Vincent Sarago"/><br /><sub><b>Vincent Sarago</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=vincentsarago" title="Code">💻</a></td>
      <td align="center"><a href="https://hotfix.guru"><img src="https://avatars.githubusercontent.com/u/5310116?v=4?s=100" width="100px;" alt="Jonas Krüger Svensson"/><br /><sub><b>Jonas Krüger Svensson</b></sub></a><br /><a href="#platform-JonasKs" title="Packaging/porting to new platform">📦</a></td>
      <td align="center"><a href="https://github.com/sondrelg"><img src="https://avatars.githubusercontent.com/u/25310870?v=4?s=100" width="100px;" alt="Sondre Lillebø Gundersen"/><br /><sub><b>Sondre Lillebø Gundersen</b></sub></a><br /><a href="#platform-sondrelg" title="Packaging/porting to new platform">📦</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://github.com/vrslev"><img src="https://avatars.githubusercontent.com/u/75225148?v=4?s=100" width="100px;" alt="Lev"/><br /><sub><b>Lev</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=vrslev" title="Code">💻</a> <a href="#ideas-vrslev" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center"><a href="https://github.com/timwedde"><img src="https://avatars.githubusercontent.com/u/20231751?v=4?s=100" width="100px;" alt="Tim Wedde"/><br /><sub><b>Tim Wedde</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=timwedde" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/tclasen"><img src="https://avatars.githubusercontent.com/u/11999013?v=4?s=100" width="100px;" alt="Tory Clasen"/><br /><sub><b>Tory Clasen</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=tclasen" title="Code">💻</a></td>
      <td align="center"><a href="http://t.me/Bobronium"><img src="https://avatars.githubusercontent.com/u/36469655?v=4?s=100" width="100px;" alt="Arseny Boykov"/><br /><sub><b>Arseny Boykov</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Bobronium" title="Code">💻</a> <a href="#ideas-Bobronium" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center"><a href="https://github.com/yudjinn"><img src="https://avatars.githubusercontent.com/u/7493084?v=4?s=100" width="100px;" alt="Jacob Rodgers"/><br /><sub><b>Jacob Rodgers</b></sub></a><br /><a href="#example-yudjinn" title="Examples">💡</a></td>
      <td align="center"><a href="https://github.com/danesolberg"><img src="https://avatars.githubusercontent.com/u/25882507?v=4?s=100" width="100px;" alt="Dane Solberg"/><br /><sub><b>Dane Solberg</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=danesolberg" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/madlad33"><img src="https://avatars.githubusercontent.com/u/54079440?v=4?s=100" width="100px;" alt="madlad33"/><br /><sub><b>madlad33</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=madlad33" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center"><a href="http://matthewtyleraylward.com"><img src="https://avatars.githubusercontent.com/u/19205392?v=4?s=100" width="100px;" alt="Matthew Aylward "/><br /><sub><b>Matthew Aylward </b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Butch78" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/Joko013"><img src="https://avatars.githubusercontent.com/u/30841710?v=4?s=100" width="100px;" alt="Jan Klima"/><br /><sub><b>Jan Klima</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Joko013" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/i404788"><img src="https://avatars.githubusercontent.com/u/50617709?v=4?s=100" width="100px;" alt="C2D"/><br /><sub><b>C2D</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=i404788" title="Tests">⚠️</a></td>
      <td align="center"><a href="https://github.com/to-ph"><img src="https://avatars.githubusercontent.com/u/84818322?v=4?s=100" width="100px;" alt="to-ph"/><br /><sub><b>to-ph</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=to-ph" title="Code">💻</a></td>
      <td align="center"><a href="https://imbev.gitlab.io/site"><img src="https://avatars.githubusercontent.com/u/105524473?v=4?s=100" width="100px;" alt="imbev"/><br /><sub><b>imbev</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=imbev" title="Documentation">📖</a></td>
      <td align="center"><a href="https://git.roboces.dev/catalin"><img src="https://avatars.githubusercontent.com/u/45485069?v=4?s=100" width="100px;" alt="cătălin"/><br /><sub><b>cătălin</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=185504a9" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/Seon82"><img src="https://avatars.githubusercontent.com/u/46298009?v=4?s=100" width="100px;" alt="Seon82"/><br /><sub><b>Seon82</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Seon82" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://github.com/slavugan"><img src="https://avatars.githubusercontent.com/u/8457612?v=4?s=100" width="100px;" alt="Slava"/><br /><sub><b>Slava</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=slavugan" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/Harry-Lees"><img src="https://avatars.githubusercontent.com/u/52263746?v=4?s=100" width="100px;" alt="Harry"/><br /><sub><b>Harry</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Harry-Lees" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=Harry-Lees" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/cofin"><img src="https://avatars.githubusercontent.com/u/204685?v=4?s=100" width="100px;" alt="Cody Fincher"/><br /><sub><b>Cody Fincher</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=cofin" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=cofin" title="Documentation">📖</a> <a href="#maintenance-cofin" title="Maintenance">🚧</a></td>
      <td align="center"><a href="https://www.patreon.com/cclauss"><img src="https://avatars.githubusercontent.com/u/3709715?v=4?s=100" width="100px;" alt="Christian Clauss"/><br /><sub><b>Christian Clauss</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=cclauss" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/josepdaniel"><img src="https://avatars.githubusercontent.com/u/36941460?v=4?s=100" width="100px;" alt="josepdaniel"/><br /><sub><b>josepdaniel</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=josepdaniel" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/devtud"><img src="https://avatars.githubusercontent.com/u/6808024?v=4?s=100" width="100px;" alt="devtud"/><br /><sub><b>devtud</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/issues?q=author%3Adevtud" title="Bug reports">🐛</a></td>
      <td align="center"><a href="https://github.com/nramos0"><img src="https://avatars.githubusercontent.com/u/35410160?v=4?s=100" width="100px;" alt="Nicholas Ramos"/><br /><sub><b>Nicholas Ramos</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=nramos0" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://twitter.com/seladb"><img src="https://avatars.githubusercontent.com/u/9059541?v=4?s=100" width="100px;" alt="seladb"/><br /><sub><b>seladb</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=seladb" title="Documentation">📖</a> <a href="https://github.com/starlite-api/starlite/commits?author=seladb" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/aedify-swi"><img src="https://avatars.githubusercontent.com/u/66629131?v=4?s=100" width="100px;" alt="Simon Wienhöfer"/><br /><sub><b>Simon Wienhöfer</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=aedify-swi" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/mobiusxs"><img src="https://avatars.githubusercontent.com/u/57055149?v=4?s=100" width="100px;" alt="MobiusXS"/><br /><sub><b>MobiusXS</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=mobiusxs" title="Code">💻</a></td>
      <td align="center"><a href="http://aidansimard.dev"><img src="https://avatars.githubusercontent.com/u/73361895?v=4?s=100" width="100px;" alt="Aidan Simard"/><br /><sub><b>Aidan Simard</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Aidan-Simard" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/waweber"><img src="https://avatars.githubusercontent.com/u/714224?v=4?s=100" width="100px;" alt="wweber"/><br /><sub><b>wweber</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=waweber" title="Code">💻</a></td>
      <td align="center"><a href="http://scolvin.com"><img src="https://avatars.githubusercontent.com/u/4039449?v=4?s=100" width="100px;" alt="Samuel Colvin"/><br /><sub><b>Samuel Colvin</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=samuelcolvin" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/toudi"><img src="https://avatars.githubusercontent.com/u/81148?v=4?s=100" width="100px;" alt="Mateusz Mikołajczyk"/><br /><sub><b>Mateusz Mikołajczyk</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=toudi" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://github.com/Alex-CodeLab"><img src="https://avatars.githubusercontent.com/u/1678423?v=4?s=100" width="100px;" alt="Alex "/><br /><sub><b>Alex </b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Alex-CodeLab" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/odiseo0"><img src="https://avatars.githubusercontent.com/u/87550035?v=4?s=100" width="100px;" alt="Odiseo"/><br /><sub><b>Odiseo</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=odiseo0" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/ingjavierpinilla"><img src="https://avatars.githubusercontent.com/u/36714646?v=4?s=100" width="100px;" alt="Javier  Pinilla"/><br /><sub><b>Javier  Pinilla</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=ingjavierpinilla" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/Chaoyingz"><img src="https://avatars.githubusercontent.com/u/32626585?v=4?s=100" width="100px;" alt="Chaoying"/><br /><sub><b>Chaoying</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Chaoyingz" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/infohash"><img src="https://avatars.githubusercontent.com/u/46137868?v=4?s=100" width="100px;" alt="infohash"/><br /><sub><b>infohash</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=infohash" title="Code">💻</a></td>
      <td align="center"><a href="https://www.linkedin.com/in/john-ingles/"><img src="https://avatars.githubusercontent.com/u/35442886?v=4?s=100" width="100px;" alt="John Ingles"/><br /><sub><b>John Ingles</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=john-ingles" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/h0rn3t"><img src="https://avatars.githubusercontent.com/u/1213719?v=4?s=100" width="100px;" alt="Eugene"/><br /><sub><b>Eugene</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=h0rn3t" title="Tests">⚠️</a> <a href="https://github.com/starlite-api/starlite/commits?author=h0rn3t" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://github.com/jonadaly"><img src="https://avatars.githubusercontent.com/u/26462826?v=4?s=100" width="100px;" alt="Jon Daly"/><br /><sub><b>Jon Daly</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=jonadaly" title="Documentation">📖</a> <a href="https://github.com/starlite-api/starlite/commits?author=jonadaly" title="Code">💻</a></td>
      <td align="center"><a href="https://harshallaheri.me/"><img src="https://avatars.githubusercontent.com/u/73422191?v=4?s=100" width="100px;" alt="Harshal Laheri"/><br /><sub><b>Harshal Laheri</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=Harshal6927" title="Code">💻</a> <a href="https://github.com/starlite-api/starlite/commits?author=Harshal6927" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/sorasful"><img src="https://avatars.githubusercontent.com/u/32820423?v=4?s=100" width="100px;" alt="Téva KRIEF"/><br /><sub><b>Téva KRIEF</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=sorasful" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/jtraub"><img src="https://avatars.githubusercontent.com/u/153191?v=4?s=100" width="100px;" alt="Konstantin Mikhailov"/><br /><sub><b>Konstantin Mikhailov</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=jtraub" title="Documentation">📖</a> <a href="https://github.com/starlite-api/starlite/commits?author=jtraub" title="Code">💻</a></td>
      <td align="center"><a href="http://linkedin.com/in/mitchell-henry334/"><img src="https://avatars.githubusercontent.com/u/17354727?v=4?s=100" width="100px;" alt="Mitchell Henry"/><br /><sub><b>Mitchell Henry</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=devmitch" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/chbndrhnns"><img src="https://avatars.githubusercontent.com/u/7534547?v=4?s=100" width="100px;" alt="chbndrhnns"/><br /><sub><b>chbndrhnns</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=chbndrhnns" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/nielsvanhooy"><img src="https://avatars.githubusercontent.com/u/40770348?v=4?s=100" width="100px;" alt="nielsvanhooy"/><br /><sub><b>nielsvanhooy</b></sub></a><br /><a href="https://github.com/starlite-api/starlite/commits?author=nielsvanhooy" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification.
Contributions of any kind welcome!
