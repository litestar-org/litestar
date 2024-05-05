Starlite library documentation
==============================


Starlite is a powerful, flexible, highly performant and opinionated ASGI framework,
offering first class typing support and a full `Pydantic <https://github.com/samuelcolvin/pydantic>`_
integration.

The Starlite framework supports :doc:`/usage/plugins/index`, ships
with :doc:`dependency injection </usage/dependency-injection>`, :doc:`security primitives </usage/security/index>`,
:doc:`OpenAPI schema generation </usage/openapi>`, `MessagePack <https://msgpack.org/>`_,
:doc:`middlewares </usage/middleware/index>` and much more.

Installation
------------

.. code-block:: shell

   pip install starlite


.. dropdown:: Extras
    :icon: star

    :ref:`Brotli Compression Middleware <usage/middleware/builtin-middleware:brotli>`:
        :code:`pip install starlite[brotli]`

    :ref:`Client-side sessions <usage/middleware/builtin-middleware:client-side sessions>`
        :code:`pip install starlite[cryptography]`

    :ref:`Server-side sessions <usage/middleware/builtin-middleware:redis storage>` / :ref:`redis caching <usage/caching:redis>`:
        :code:`pip install starlite[redis]`

    :ref:`Server-side sessions <usage/middleware/builtin-middleware:memcached storage>` / :ref:`memcached caching <usage/caching:memcached>`:
        :code:`pip install starlite[memcached]`

    :ref:`Picologging <usage/the-starlite-app:using picologging>`
        :code:`pip install starlite[picologging]`

    :ref:`StructLog <usage/the-starlite-app:using structlog>`
        :code:`pip install starlite[structlog]`

    :doc:`/usage/contrib/open-telemetry`
        :code:`pip install starlite[openetelemetry]`

    :doc:`/usage/cli`
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
        async def create_user(self, data: User) -> User: ...

        @get()
        async def list_users(self) -> List[User]: ...

        @patch(path="/{user_id:uuid}")
        async def partial_update_user(
            self, user_id: UUID4, data: Partial[User]
        ) -> User: ...

        @put(path="/{user_id:uuid}")
        async def update_user(self, user_id: UUID4, data: User) -> User: ...

        @get(path="/{user_id:uuid}")
        async def get_user(self, user_id: UUID4) -> User: ...

        @delete(path="/{user_id:uuid}")
        async def delete_user(self, user_id: UUID4) -> None: ...


When instantiating your app, import your *controller* into your application's
entry-point and pass it to Starlite:

.. code-block:: python

   from starlite import Starlite

   from my_app.controllers.user import UserController

   app = Starlite(route_handlers=[UserController])

To **run your application**, use an ASGI server such as `uvicorn <https://www.uvicorn.org/>`_ :

.. code-block:: shell

   uvicorn my_app.main:app --reload


Philosophy
----------

- Starlite is a community-driven project. This means not a single author,
  but rather a core team of maintainers is leading the project, supported by a community
  of contributors. Starlite currently has 5 maintainers and is being very actively developed.
- Starlite draws inspiration from `NestJS <https://nestjs.com/>`_ - a contemporary TypeScript framework - which places
  opinions and patterns at its core.
- While still allowing for **function-based endpoints**, Starlite seeks to build on Python's powerful and versatile
  OOP, by placing **class-based controllers** at its core.
- Starlite is **not** a microframework. Unlike frameworks such as FastAPI, Starlette or Flask, Starlite includes a lot
  of functionalities out of the box needed for a typical modern web application, such as ORM integration,
  client- and server-side sessions, caching, OpenTelemetry integration and many more. It's not aiming to be "the next
  Django" (for example, it will never feature its own ORM), but its scope is not micro either.


Feature comparison with similar frameworks
------------------------------------------

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


Example Applications
--------------------


* `starlite-pg-redis-docker <https://github.com/starlite-api/starlite-pg-redis-docker>`_ : In addition to Starlite, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Starlite projects, this application is open to contributions, big and small.
* `starlite-hello-world <https://github.com/starlite-api/starlite-hello-world>`_: A bare-minimum application setup. Great
  for testing and POC work.


.. toctree::
    :titlesonly:
    :caption: Documentation
    :hidden:

    usage/index
    reference/index
    migration/index
    benchmarks
