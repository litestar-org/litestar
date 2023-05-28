Litestar library documentation
==============================

Litestar is a powerful, flexible, highly performant and opinionated ASGI framework,
offering first class typing support and a full `Pydantic <https://github.com/pydantic/pydantic>`_
integration.

The Litestar framework supports :doc:`/usage/plugins`, ships
with :doc:`dependency injection </usage/dependency-injection>`, :doc:`security primitives </usage/security/index>`,
:doc:`OpenAPI schema generation </usage/openapi>`, `MessagePack <https://msgpack.org/>`_,
:doc:`middlewares </usage/middleware/index>` and much more.

Installation
------------

.. code-block:: shell

   pip install litestar


.. dropdown:: Extras
    :icon: star

    :ref:`Brotli Compression Middleware <usage/middleware/builtin-middleware:brotli>`:
        :code:`pip install litestar[brotli]`

    :ref:`Cookie Based Sessions <usage/middleware/builtin-middleware:client-side sessions>`
        :code:`pip install litestar[cryptography]`

    :doc:`JWT Security Backends </usage/contrib/jwt>`
        :code:`pip install litestar[jwt]`

    :doc:`RedisStore </usage/stores>`
        :code:`pip install litestar[redis]`

    :ref:`Picologging <usage/the-litestar-app:using picologging>`
        :code:`pip install litestar[picologging]`

    :ref:`StructLog <usage/the-litestar-app:using structlog>`
        :code:`pip install litestar[structlog]`

    :doc:`Open Telemetry Instrumentation </usage/contrib/open-telemetry>`
        :code:`pip install litestar[openetelemetry]`

    :doc:`SQLAlchemy </usage/contrib/sqlalchemy/index>`
        :code:`pip install litestar[sqlalchemy]`

    :doc:`CLI </usage/cli>`
        :code:`pip install litestar[cli]`

    :doc:`Jinja Templating </usage/templating>`
        :code:`pip install litestar[jinja]`

    Attrs
        :code:`pip install litestar[attrs]`

    Standard Installation (includes CLI and Jinja templating):
        :code:`pip install litestar[standard]`

    All Extras:
        :code:`pip install litestar[full]`



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
    from litestar import Controller, get, post, put, patch, delete
    from litestar.partial import Partial
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
entry-point and pass it to Litestar:

.. code-block:: python

   from litestar import Litestar

   from my_app.controllers.user import UserController

   app = Litestar(route_handlers=[UserController])

To **run your application**, use an ASGI server such as `uvicorn <https://www.uvicorn.org/>`_ :

.. code-block:: shell

   uvicorn my_app.main:app --reload


Philosophy
----------

- Litestar is a community-driven project. This means not a single author,
  but rather a core team of maintainers is leading the project, supported by a community
  of contributors. Litestar currently has 5 maintainers and is being very actively developed.
- Litestar draws inspiration from `NestJS <https://nestjs.com/>`_ - a contemporary TypeScript framework - which places
  opinions and patterns at its core.
- While still allowing for **function-based endpoints**, Litestar seeks to build on Python's powerful and versatile
  OOP, by placing **class-based controllers** at its core.
- Litestar is **not** a microframework. Unlike frameworks such as FastAPI, Starlette or Flask, Litestar includes a lot
  of functionalities out of the box needed for a typical modern web application, such as ORM integration,
  client- and server-side sessions, caching, OpenTelemetry integration and many more. It's not aiming to be "the next
  Django" (for example, it will never feature its own ORM), but its scope is not micro either.


Feature comparison with similar frameworks
------------------------------------------

+-----------------------------+------------------------------------+---------------------+------------------+---------------------+---------------------+
|                             | Litestar                           | FastAPI             | Starlette        | Sanic               | Quart               |
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


* `litestar-pg-redis-docker <https://github.com/litestar-org/starlite-pg-redis-docker>`_ : In addition to Litestar, this
  demonstrates a pattern of application modularity, SQLAlchemy 2.0 ORM, Redis cache connectivity, and more. Like all
  Litestar projects, this application is open to contributions, big and small.
* `litestar-hello-world <https://github.com/litestar-org/litestar-hello-world>`_: A bare-minimum application setup. Great
  for testing and POC work.


.. toctree::
    :titlesonly:
    :caption: Documentation
    :hidden:

    tutorials/index
    usage/index
    reference/index
    topics/index
    migration/index
    benchmarks
