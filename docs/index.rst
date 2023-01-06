Welcome to Starlite's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Starlite is a powerful, flexible, highly performant and opinionated ASGI framework,
offering first class typing support and a full `Pydantic <https://github.com/samuelcolvin/pydantic>`_
integration.

The Starlite framework supports `plugins <usage/10-plugins/0-plugins-intro.md>`_ , ships
with `dependency injection <usage/6-dependency-injection/0-dependency-injection-intro.md>`,
`security primitives <usage/8-security/0-intro.md>`_ ,
`OpenAPI specifications-generation <usage/12-openapi/0-openapi-intro.md>`_ ,
`MessagePack <https://msgpack.org/>`_ support – among other common API-framework components such
as `middleware <usage/7-middleware/middleware-intro.md>`_.

Installation
------------

.. code-block:: shell

   pip install starlite


.. dropdown:: Extras
    :icon: star

    [Brotli Compression Middleware](usage/7-middleware/builtin-middlewares#brotli):
        :code:`pip install starlite[brotli]`

    [Client-side sessions](usage/7-middleware/builtin-middlewares#client-side-sessions)
        :code:`pip install starlite[cryptography]`

    [Server-side sessions with redis](usage/7-middleware/builtin-middlewares#redis-storage) / [redis caching](usage/15-caching/0-cache-backends):
        :code:`pip install starlite[redis]`

    [Server-side sessions with memcached](usage/7-middleware/builtin-middlewares#memcached-storage) / [memcached caching](usage/15-caching/0-cache-backends):
        :code:`pip install starlite[memcached]`

    [Picologging](usage/0-the-starlite-app/4-logging/#using-picologging):
        :code:`pip install starlite[picologging]`

    [StructLog](usage/0-the-starlite-app/4-logging/#using-structlog):
        :code:`pip install starlite[structlog]`

    [OpenTelemetry](usage/18-contrib/0-open-telemetry/):
        :code:`pip install starlite[openetelemetry]`

    [CLI](usage/19-cli):
        :code:`pip install starlite[cli]`

    Standard installation (includes CLI, picologging and Jinja2 templating):
        :code:`pip install starlite[standard]`

    All extras:
        :code:`pip install starlite[full]`



Minimal Example
---------------

**Define your data model** using pydantic or any library based on it (for example ormar, beanie, SQLModel):

.. code-block:: python

    from pydantic import BaseModel, UUID4


    class User(BaseModel):
        first_name: str
        last_name: str
        id: UUID4




You can also use dataclasses (standard library and Pydantic),
:class:`typing.TypedDict` or :class:`msgspec.Struct`.

.. code-block:: python

   from uuid import UUID

   # from pydantic.dataclasses import dataclass
   from dataclasses import dataclass


   @dataclass
   class User:
       first_name: str
       last_name: str
       id: UUID

**Define a Controller for your data model:**

.. code-block:: python

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


When instantiating your app, import your *controller* into your application's
entry-point and pass it to Starlite:

.. code-block:: python

   from starlite import Starlite

   from my_app.controllers.user import UserController

   app = Starlite(route_handlers=[UserController])

To **run your application**, use an ASGI server such as `uvicorn <https://www.uvicorn.org/>`_ :

.. code-block:: shell

   uvicorn my_app.main:app --reload


Example Applications
--------------------


* `starlite-pg-redis-docker <https://github.com/starlite-api/starlite-pg-redis-docker>`_ : In addition to Starlite, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Starlite projects, this application is open to contributions, big and small.
* `starlite-hello-world <https://github.com/starlite-api/starlite-hello-world>`_: A bare-minimum application setup. Great
  for testing and POC work.

About Starlite
--------------

- Starlite is a community-driven project. This means not a single author,
  but rather a core team of maintainers is leading the project, supported by a community
  of contributors. Starlite currently has 5 maintainers and is being very actively developed.
- Starlite draws inspiration from `NestJS <https://nestjs.com/>`_ - a contemporary TypeScript framework - which places
  opinions and patterns at its core.
- While still allowing for **function-based endpoints**\ , Starlite seeks to build on Python's powerful and versatile
  OOP, by placing **class-based controllers** at its core.
- Starlite is **not** a microframework. Unlike frameworks such as FastAPI, Starlette or Flask, Starlite includes a lot
  of functionalities out of the box needed for a typical modern web application, such as ORM integration,
  client- and server-side sessions, caching, OpenTelemetry integration and many more. It's not aiming to be "the next
  Django" (for example, it will never feature its own ORM), but its scope is not micro either.


Comparison with other frameworks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
|                             | Starlite                           | FastAPI             | Starlette        | Sanic               | Quart               |
+=============================+====================================+=====================+==================+=====================+=====================+
| OpenAPI                     | :octicon:`check`                   | :octicon:`check`    | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Automatic API documentation | Swagger, ReDoc, Stoplight Elements | Swagger, ReDoc      | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Data validation             | :octicon:`check`                   | :octicon:`check`    | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Dependency Injection        | :octicon:`check`                   | :octicon:`check`    | :octicon:`dash`  | :octicon:`check`    | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Class based routing         | :octicon:`check`                   | (Through extension) | :octicon:`check` | :octicon:`check`    | :octicon:`check`    |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| ORM integration             | SQLAlchemy, Tortoise, Piccolo      | :octicon:`dash`     | :octicon:`dash`  | :octicon:`dash`     | (Through extension) |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Templating                  | Jinja, Mako                        | Jinja               | Jinja            | Jinja               | Jinja               |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| MessagePack                 | :octicon:`check`                   | :octicon:`dash`     | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| CORS                        | :octicon:`check`                   | :octicon:`check`    | :octicon:`check` | :octicon:`check`    | (Through extension) |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| CSRF                        | :octicon:`check`                   | :octicon:`dash`     | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Rate-limiting               | :octicon:`check`                   | :octicon:`dash`     | :octicon:`dash`  | (Through extension) | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| JWT                         | :octicon:`check`                   | :octicon:`dash`     | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Sessions                    | :octicon:`check`                   | Client-side         | Client-side      | :octicon:`dash`     | Client-side         |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Authentication              | JWT / Session based                | :octicon:`dash`     | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
| Caching                     | :octicon:`check`                   |  :octicon:`dash`    | :octicon:`dash`  | :octicon:`dash`     | :octicon:`dash`     |
+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+



Project Governance
^^^^^^^^^^^^^^^^^^

From its inception, Starlite was envisaged as a community driven project. We encourage users to become involved with the
project - feel free to open issues, chime in on discussions, review pull requests and of course - contribute code.

The project is led by a group of maintainers. You can see the list of maintainers in the ``pyproject.toml`` file.
Additionally, substantial contributors are invited to be members of the ``starlite-api`` organization. Our aim is to
increase the number of maintainers and have at least 5 active maintainers - this will ensure the long term stability and
growth of Starlite in the long run. Contributors who show commitment, contribute great code and show a willingness to
become maintainers will be invited to do so. So really feel free to contribute and propose yourself as a maintainer once
you contribute substantially.

Contribution Guide
^^^^^^^^^^^^^^^^^^

Any and all contributions and involvement with the project is welcome. The easiest way to begin contributing
is to check out the open issues - and reach out on our discord server or Matrix space.


License
^^^^^^^

.. include:: ../LICENSE
