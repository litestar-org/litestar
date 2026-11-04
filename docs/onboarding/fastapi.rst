FastAPI
=======


Layered configuration
---------------------

Litestar uses a layered architecture. The parts used to group routes can also be used
to hierarchically organize an application. Settings and configuration like
dependencies, exception handlers, guards, middleware, response cookies and headers,
lifecycle hooks, OpenAPI configuration and many more can be defined on any layer, and
will be merged upon registration.

The layers in hierarchical order are

1. Application (``Litestar``)
2. ``Router`` / ``Controller`` (these are on the same level and can be arbitrarily nested)
3. Handler (``BaseRouteHandler``)

When the same configuration is set on multiple layers, the value set closest to the
handler takes precedence.


Pydantic support
----------------

Litestar does support Pydantic, but other than FastAPI, it is mostly agnostic about
the modelling library you use. Litestar internally uses
`msgspec <https://msgspec.dev>`_, but also ships with support for Pydantic,
attrs and all builtin container types such as dataclasses or ``TypedDict``\ s.

These, as well as ``msgspec``, are supported through its plugin system (
:class:`~litestar.plugins.SerializationPlugin` and
:class:`~litestar.plugins.OpenAPISchemaPlugin`) so it's easy to add first-class support
for any library.


Route handlers
--------------

Litestar does not expose decorators on the application or router. A route is declared by
a :doc:`route handler </usage/routing/handlers>` (function with one of the method
decorators, or a method on a :class:`Controller`) and then registered on a
:class:`Litestar` or :class:`Router` instance.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI

            app = FastAPI()

            @app.get("/")
            async def index() -> dict[str, str]: ...

    .. tab-item:: Starlette
        :sync: starlette

        .. code-block:: python

            from starlette.applications import Starlette
            from starlette.routing import Route

            async def index(request): ...

            routes = [Route("/", endpoint=index)]
            app = Starlette(routes=routes)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/routing.py
            :language: python

.. seealso::

    * :ref:`Routing - Registering Routes <usage/routing/overview:registering routes>`


Routers
~~~~~~~

A few small differences between Litestar's :class:`Router` and FastAPI / Starlette's:

- A Litestar ``Router`` is not itself an ASGI application. It groups handlers and
  options. Routers are "flattened" into simple handlers during registration
- A Litestar ``Router`` does not expose decorators
- A Litestar ``Router`` does not run lifecycle hooks. Lifecycle hooks can only be
  registered on the application. See :doc:`/usage/lifecycle-hooks` for more information


Host-based routing
~~~~~~~~~~~~~~~~~~

Litestar does not support dispatching requests by the ``Host`` header. Run
each host as its own application behind a reverse proxy such as
`nginx <https://www.nginx.com>`_ or `traefik <https://traefik.io>`_.


Lifespan
~~~~~~~~

Litestar uses the async context manager pattern as Starlette/FastAPI:

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def lifespan(app: FastAPI):
                # setup
                yield
                # teardown

            app = FastAPI(lifespan=lifespan)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/lifespan.py
            :language: python


Application state
~~~~~~~~~~~~~~~~~

Application-scoped data lives on :class:`~litestar.datastructures.State`, the equivalent
of FastAPI's ``app.state``. State seeded on the application is available to dependencies
through the ``state`` parameter and to handlers through ``request.app.state``.
Per-request data lives on ``request.state`` instead, and is wiped between requests.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Request

            async def get_arq_redis(request: Request) -> ArqRedis:
                return request.state.arq_redis

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/state.py
            :language: python


Handlers and request data
-------------------------

Path and query parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

FastAPI allows declaring path and query parameters implicitly; If a function parameter
of the same name is detected, the path / query parameter will be injected into it.
Litestar uses the same mechanism but makes it explicit: The corresponding parameters
must be marked with :data:`~litestar.params.FromPath` and
:data:`~litestar.params.FromQuery` respectively:

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/{some_path}")
            async def handler(some_path: str, some_query: int) -> None:
                return None

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/parameters.py
            :language: python


To define constraints or extend the OpenAPI schema for parameters, use their
``Annotated`` shapes :class:`~litestar.params.PathParameter` and
:class:`~litestar.params.QueryParameter`:

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/{some_path}")
            async def handler(
                some_path: str,
                some_query: Annotated[int, Query(gt=1)],
            ) -> None:
                return None

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/parameters_constrained.py
            :language: python

See :doc:`/usage/routing/parameters` for more details.



Header and cookie parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These take the same shape as :ref:`onboarding/fastapi:Path and query parameters`, with
their generic forms :data:`~litestar.params.FromHeader` and
:data:`~litestar.params.FromCookie`. One important difference between FastAPI and
Litestar is, that FastAPI automatically matches snake case parameter names to cookie /
header names (e.g. ``some_header: Annotated[str, Header()]`` will match the header
``Some-Header``). Litestar requires specifying the name explicitly if it does not match
the function parameter name.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/")
            async def handler(
                some_cookie: Annotated[int, Cookie(lt=10)],
                some_header: Annotated[int, Header(gt=1)],
            ) -> None:
                return None

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/header_cookie_params.py
            :language: python


JSON request body
~~~~~~~~~~~~~~~~~

The JSON body binds is injected into the handler via the ``data`` parameter. Its type
can be any type supported by Litestar or a validation extension. The data will be
validated against this type before it is passed to the handler.

Litestar natively supports builtin types, dataclasses, Pydantic models, msgspec
``Struct``\ s and attrs classes.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            class Item(BaseModel):
                name: str

            @app.post("/items/")
            async def create_item(item: Item) -> dict[str, str]:
                return {"name": item.name}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/post_json.py
            :language: python


Form data
~~~~~~~~~

Form-encoded bodies use the same ``data`` parameter, annotated with
:func:`~litestar.params.Body` and a ``media_type`` of
:class:`RequestEncodingType.URL_ENCODED <litestar.enums.RequestEncodingType>` or
:class:`RequestEncodingType.MULTI_PART <litestar.enums.RequestEncodingType>`

One ``data`` declaration replaces FastAPI's per-field ``Form()`` calls.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Form

            @app.post("/login")
            async def login(
                username: str = Form(...),
                password: str = Form(...),
            ) -> dict[str, str]:
                return {"user": username}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/form_data.py
            :language: python


File uploads
~~~~~~~~~~~~

Multipart bodies use the same ``data`` parameter with ``media_type`` set
to :class:`RequestEncodingType.MULTI_PART <litestar.enums.RequestEncodingType>`.
Uploaded files arrive as :class:`~litestar.datastructures.UploadFile`
instances. To receive multiple files, you can simply use ``list[UploadFile]``. For mixed
form data (i.e. plain fields + uploads), you can simply annotate any field of a supported
model type with ``UploadData``.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import UploadFile

            @app.post("/upload/")
            async def upload(files: list[UploadFile]) -> dict[str, list[str]]:
                return {"file_names": [f.filename for f in files]}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/uploads.py
            :language: python


Synchronous handlers
~~~~~~~~~~~~~~~~~~~~

FastAPI inspects the handler at registration and runs synchronous callables on a
threadpool. Litestar has the same mechanism, but it must be explicitly enabled by
setting ``sync_to_thread=True``. A synchronous handler without ``sync_to_thread`` will
emit a warning at startup. If you intentionally do not want to run a synchronous handler
inside a thread pool, set ``sync_to_thread=False``.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/")
            def slow_handler() -> dict[str, str]:
                # implicitly run in a threadpool
                return {"hello": "world"}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/sync_handler.py
            :language: python



Producing responses
-------------------

Default status codes
~~~~~~~~~~~~~~~~~~~~

FastAPI returns ``200`` for every method by default. Litestar picks the status code
from the HTTP method: ``POST`` defaults to ``201 Created``, ``DELETE`` to
``204 No Content``, and everything else to ``200``. You can pass ``status_code=`` to
the handler to override the default status code.

Cookies and headers
~~~~~~~~~~~~~~~~~~~

FastAPI defaults to setting headers directly on a ``Response`` . Litestar offers two
paths: declare static values on the decorator with ``response_cookies`` and
``response_headers``, or return a :class:`~litestar.response.Response` with ``cookies=``
and ``headers=`` when the values depend on the request.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Response

            @app.get("/")
            async def index(response: Response) -> dict[str, str]:
                response.set_cookie(key="my-cookie", value="cookie-value")
                return {}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/cookies.py
            :language: python

.. seealso::

    * :ref:`Responses - Setting Response Cookies <usage/responses:setting response cookies>`


Serialization
~~~~~~~~~~~~~

The handler's return annotation drives serialization. Structured types serialise to
JSON; ``str`` returns ``text/plain``; a typed response (``Stream``, ``Template``,
``Redirect``, ``File``) picks its own media type. ``media_type=`` on the decorator
overrides the default.


Templates
~~~~~~~~~

FastAPI renders templates through Starlette's ``Jinja2Templates`` helper and returns a
``TemplateResponse``. In Litestar the engine is configured once on the application
through :class:`~litestar.template.config.TemplateConfig`, and each handler returns a
:class:`~litestar.response.Template`.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi.templating import Jinja2Templates

            templates = Jinja2Templates(directory="templates")

            @app.get("/uploads")
            async def get_uploads(request: Request):
                return templates.TemplateResponse(
                    "uploads.html", {"request": request, "debug": True}
                )

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/templates.py
            :language: python

.. seealso::

    * :doc:`/usage/templating`


Streaming responses
~~~~~~~~~~~~~~~~~~~

FastAPI uses ``StreamingResponse``; Litestar uses :class:`~litestar.response.Stream`.
Both wrap a sync or async iterator.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi.responses import StreamingResponse

            @app.get("/numbers")
            async def stream_numbers() -> StreamingResponse:
                async def numbers():
                    for i in range(5):
                        yield f"{i}\n".encode()

                return StreamingResponse(numbers())

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/streaming.py
            :language: python


Dependency injection
--------------------

FastAPI declares a dependency at the call site, either as a default value or inside the
parameter annotation via ``Depends(fn)``, or in a list on the path operation.
Litestar declares dependencies as a mapping from parameter name to provider, attached to
the ``dependencies`` keyword on any layer. Async callables can be used as dependency
providers natively, sync callables must be wrapped in :class:`~litestar.di.Provide`.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI, Depends, APIRouter

            async def route_dependency() -> bool: ...
            async def nested_dependency() -> str: ...
            async def router_dependency() -> int: ...
            async def app_dependency(data: str = Depends(nested_dependency)) -> int: ...

            router = APIRouter(dependencies=[Depends(router_dependency)])
            app = FastAPI(dependencies=[Depends(nested_dependency)])
            app.include_router(router)

            @app.get("/")
            async def handler(
                val_route: bool = Depends(route_dependency),
                val_router: int = Depends(router_dependency),
                val_nested: str = Depends(nested_dependency),
                val_app: int = Depends(app_dependency),
            ) -> None: ...

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/dependency_injection.py
            :language: python

.. note::

    As most configuration in Litestar, dependencies are layered. Inner layers override
    outer ones, so a router-scoped dependency replaces an application-scoped one of the
    same name, and a handler-scoped one replaces both.


.. seealso::

    * :doc:`/usage/dependency-injection`


Dependency overrides in tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FastAPI exposes ``app.dependency_overrides`` for swapping dependencies on a live
application. Litestar does not. The omission is deliberate: an override that mutates a
hared application is hard to reason about under parallel tests, and Litestar is of the
opinion that it's better to structure the application in such a way that overrides are
not necessary.

Alternative strategies are, order of preference:

1. Build the application from a factory that takes the dependencies your tests need to
   swap. Natural choice when the override exists to replace a real database with a test
   one
2. Construct a fresh application per test with
   :func:`~litestar.testing.create_test_client`, passing the overridden dependency
   through the same ``dependencies=`` keyword the production application uses
3. Patch the dependency callable with a mocking library: A last resort reserved for
   cases where first two are impractical reach


Exceptions and error responses
------------------------------

Both frameworks export an ``HTTPException``. The FastAPI one takes the status code as a
positional argument; the Litestar one uses the keyword argument ``status_code``. A
positional argument to Litestar's :class:`~litestar.exceptions.HTTPException` is
appended to ``detail``, which is rendered in the JSON response.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import HTTPException

            @app.get("/")
            async def index() -> None:
                raise HTTPException(400, detail="can't find that")

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/exceptions.py
            :language: python


Custom exception handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

FastAPI registers exception handlers through ``@app.exception_handler``. Litestar
accepts a mapping from exception class or status code to a handler callable.

.. tip::
    Exception handling is part of Litestar's layered architecture, so these can be
    declared on applications, routers, controller or route handlers

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            class ItemNotFound(Exception): ...

            @app.exception_handler(ItemNotFound)
            async def handle(request, exc) -> JSONResponse:
                return JSONResponse({"detail": "item not found"}, status_code=404)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/custom_exception_handler.py
            :language: python

.. seealso::

    * :ref:`usage/exceptions:exception handling`


Authentication
--------------

FastAPI usually handles authentication through dependency injection. The same approach
work in Litestar, but the more idiomatic choice is a guard or a custom
:doc:`/usage/security/abstract-authentication-middleware`.

.. admonition:: Info

    A guard is a callable that receives the :class:`~litestar.connection.ASGIConnection`
    and the :class:`~litestar.handlers.BaseRouteHandler`; raising an exception here
    aborts the request.

.. tip::
    Guards are part of Litestar's layered architecture, so these can be declared on
    applications, routers, controller or route handlers

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Depends

            async def authenticate(request: Request) -> None: ...

            @app.get("/", dependencies=[Depends(authenticate)])
            async def index() -> dict[str, str]: ...

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/authentication.py
            :language: python

.. seealso::

    * :doc:`/usage/security/index`


Middleware
----------

Pure ASGI middleware - a callable that wraps an ASGI app and returns another - works
the same in both frameworks. Middleware built on Starlette's ``BaseHTTPMiddleware`` does
not port directly: use :class:`~litestar.middleware.ASGIMiddleware` instead.
Subclass it and implement :meth:`~litestar.middleware.ASGIMiddleware.handle`, which
receives ``scope``, ``receive``, ``send``, and a ``next_app`` callable (the equivalent
of ``call_next``).

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from starlette.middleware.base import BaseHTTPMiddleware

            class ProcessTimeMiddleware(BaseHTTPMiddleware):
                async def dispatch(self, request, call_next):
                    start = time.monotonic()
                    response = await call_next(request)
                    response.headers["x-process-time"] = f"{time.monotonic() - start:.4f}"
                    return response

            app.add_middleware(ProcessTimeMiddleware)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/middleware.py
            :language: python

.. seealso::

    * :doc:`/usage/middleware/creating-middleware`


Background tasks
----------------

FastAPI injects a ``BackgroundTasks`` object into the handler. In Litestar, a
:class:`~litestar.background_tasks.BackgroundTask` (or a
:class:`~litestar.background_tasks.BackgroundTasks` collection) can be passed directly to
the response. These tasks run after the response body has been sent.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import BackgroundTasks

            @app.get("/")
            async def greeter(tasks: BackgroundTasks) -> dict[str, str]:
                tasks.add_task(log_visit, "world")
                return {"hello": "world"}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/background_tasks.py
            :language: python


WebSockets
-----------

FastAPI exposes a single ``@app.websocket`` decorator for direct connection handling.
Litestar offers three handler styles for the three patterns that recur in WebSocket code:

- :func:`~litestar.handlers.websocket`: Raw
  `ASGI WebSocket <https://asgi.readthedocs.io/en/latest/specs/www.html#websocket>`_
  handling, same semantics as ``@app.websocket``
- :func:`~litestar.handlers.websocket_listener`: Per-message callback style that takes
  and returns typed values; the framework handles accept, the receive loop, and
  serialisation.
- :func:`~litestar.handlers.websocket_stream`: Async generator to produce messages that
  are pushed to the WebSocket;  the framework handles accept, the receive loop, and
  serialisation.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import WebSocket

            @app.websocket("/ws")
            async def echo(socket: WebSocket) -> None:
                await socket.accept()
                while True:
                    data = await socket.receive_json()
                    await socket.send_json({"echo": data["message"]})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/websockets.py
            :language: python

For broadcast and pub/sub patterns, pair these handlers with the
:doc:`channels </usage/channels>` plugin. Channels handles per-channel subscriptions,
history, and inter-process fan-out through a pluggable broker, and can generate
WebSocket route handlers that publish incoming events to subscribed clients.

.. seealso::

    * :doc:`/usage/websockets`


Testing
-------

Both frameworks ship an ``httpx``-based ``TestClient``. The Litestar one is
:class:`~litestar.testing.TestClient`. For unit testing, Litestar also provides
:func:`~litestar.testing.create_test_client` and
:func:`~litestar.testing.create_async_test_client`, which take the same
arguments as :class:`Litestar` and return a configured client.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi.testclient import TestClient

            def test_index() -> None:
                with TestClient(app) as client:
                    response = client.get("/")
                assert response.status_code == 200

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/test_handler.py
            :language: python

.. seealso::

    * :doc:`/usage/testing`


OpenAPI customisation
---------------------

Per-route OpenAPI metadata (``tags``, ``summary``, ``description``,``operation_id``,
etc.) sits on the handler decorator in both frameworks. Application-wide options live on
:class:`~litestar.openapi.config.OpenAPIConfig`, passed as
``openapi_config=`` to the application.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get(
                "/items/{item_id}",
                tags=["items"],
                summary="Retrieve an item",
                description="Look up a single item by its numeric identifier.",
                operation_id="get_item_by_id",
            )
            async def get_item(item_id: int) -> dict[str, int]:
                return {"id": item_id}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/fastapi/openapi.py
            :language: python

.. seealso::

    * :doc:`/usage/openapi/index`


.. _fastapi-migration-quick-reference:

Quick reference
---------------

A lookup table for the most common translations.

+--------------------------------+--------------------------------------+------------------------------------------+
| Concept                        | FastAPI / Starlette                  | Litestar                                 |
+================================+======================================+==========================================+
| Route declaration              | ``@app.get("/")``                    | ``@get("/")`` + ``Litestar([handler])``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Synchronous handler            | implicit threadpool                  | ``@get(sync_to_thread=True)``            |
+--------------------------------+--------------------------------------+------------------------------------------+
| Dependency injection           | ``Depends(fn)``                      | ``dependencies={"name": Provide(fn)}``   |
+--------------------------------+--------------------------------------+------------------------------------------+
| Application state              | ``request.app.state``                | ``state: State`` + ``request.app.state`` |
+--------------------------------+--------------------------------------+------------------------------------------+
| Lifespan                       | ``@asynccontextmanager``             | ``lifespan=[ctx_mgr]``                   |
+--------------------------------+--------------------------------------+------------------------------------------+
| JSON body                      | ``item: Item``                       | ``data: Item``                           |
+--------------------------------+--------------------------------------+------------------------------------------+
| Form data                      | ``Form()``                           | ``Body(media_type=URL_ENCODED)``         |
+--------------------------------+--------------------------------------+------------------------------------------+
| File upload                    | ``UploadFile``                       | ``UploadFile`` + ``Body(MULTI_PART)``    |
+--------------------------------+--------------------------------------+------------------------------------------+
| Default POST status            | ``200``                              | ``201``                                  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Default DELETE status          | ``200``                              | ``204``                                  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Cookies                        | ``response.set_cookie``              | ``response_cookies=[Cookie(...)]``       |
+--------------------------------+--------------------------------------+------------------------------------------+
| Templates                      | ``Jinja2Templates``                  | ``Template()`` + ``TemplateConfig``      |
+--------------------------------+--------------------------------------+------------------------------------------+
| HTTPException                  | ``HTTPException(400, ...)``          | ``HTTPException(status_code=400, ...)``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Exception handler              | ``@app.exception_handler``           | ``exception_handlers={Exc: handler}``    |
+--------------------------------+--------------------------------------+------------------------------------------+
| Authentication                 | ``Depends`` chain                    | guard or auth middleware                 |
+--------------------------------+--------------------------------------+------------------------------------------+
| Dependency overrides           | ``app.dependency_overrides``         | factory + ``create_test_client``         |
+--------------------------------+--------------------------------------+------------------------------------------+
| Middleware                     | ``BaseHTTPMiddleware``               | ``ASGIMiddleware`` subclass              |
+--------------------------------+--------------------------------------+------------------------------------------+
| Background task                | ``BackgroundTasks`` injection        | ``Response(background=BackgroundTask)``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Streaming response             | ``StreamingResponse``                | ``Stream(iterator)``                     |
+--------------------------------+--------------------------------------+------------------------------------------+
| WebSocket                      | ``@app.websocket("/ws")``            | ``@websocket_listener("/ws")``           |
+--------------------------------+--------------------------------------+------------------------------------------+
| Test client                    | ``TestClient(app)``                  | ``TestClient`` / ``create_test_client``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| OpenAPI customisation          | per-decorator keywords               | per-decorator keywords + OpenAPIConfig   |
+--------------------------------+--------------------------------------+------------------------------------------+
