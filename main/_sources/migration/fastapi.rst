From Starlette / FastAPI
------------------------

Routing Decorators
~~~~~~~~~~~~~~~~~~

Litestar does not include any decorator as part of the ``Router`` or ``Litestar`` instances.
Instead, all routes are declared using :doc:`route handlers </usage/routing/handlers>`, either as standalone functions or
controller methods. The handler can then be registered on an application or router instance.

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

        .. code-block:: python

           from litestar import Litestar, get


           @get("/")
           async def index() -> dict[str, str]: ...


           app = Litestar([index])


..  seealso::

    To learn more about registering routes, check out this chapter
    in the documentation:

    * :ref:`Routing - Registering Routes <usage/routing/overview:registering routes>`

Routers and Routes
~~~~~~~~~~~~~~~~~~

There are a few key differences between Litestar’s and Starlette’s ``Router`` class:

1. The Litestar version is not an ASGI app
2. The Litestar version does not include decorators: Use :doc:`route handlers </usage/routing/handlers>`.
3. The Litestar version does not support lifecycle hooks: Those have to be handled on the application layer. See :doc:`lifecycle hooks </usage/lifecycle-hooks>`

If you are using Starlette’s ``Route``\ s, you will need to replace these with :doc:`route handlers </usage/routing/handlers>`.

Host based routing
~~~~~~~~~~~~~~~~~~

Host based routing class is intentionally unsupported. If your application relies on ``Host`` you will have to separate
the logic into different services and handle this part of request dispatching with a proxy server like `nginx <https://www.nginx.com/>`_
or `traefik <https://traefik.io/>`_.

Dependency Injection
~~~~~~~~~~~~~~~~~~~~

The Litestar dependency injection system is different from the one used by FastAPI. You can read about it in
the :doc:`dependency injection </usage/dependency-injection>` section of the documentation.

In FastAPI you declare dependencies either as a list of functions passed to the ``Router`` or ``FastAPI`` instances, or as a
default function argument value wrapped in an instance of the ``Depends`` class.

In Litestar **dependencies are always declared using a dictionary** with a string key and the value wrapped in an
instance of the ``Provide`` class. This also allows to transparently override dependencies on every level of the application,
and to easily access dependencies from higher levels.

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

        .. code-block:: python

           from litestar import Litestar, get, Router
           from litestar.di import Provide


           async def route_dependency() -> bool: ...


           async def nested_dependency() -> str: ...


           async def router_dependency() -> int: ...


           async def app_dependency(nested: str) -> int: ...


           @get("/", dependencies={"val_route": Provide(route_dependency)})
           async def handler(
               val_route: bool, val_router: int, val_nested: str, val_app: int
           ) -> None: ...


           router = Router(dependencies={"val_router": Provide(router_dependency)})
           app = Litestar(
               route_handlers=[handler],
               dependencies={
                   "val_app": Provide(app_dependency),
                   "val_nested": Provide(nested_dependency),
               },
           )


..  seealso::

    To learn more about dependency injection, check out this chapter
    in the documentation:

    * :doc:`/usage/dependency-injection`

Lifespan
~~~~~~~~

Litestar uses the same async context manager style as FastAPI, so the code does not need to be changed:

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @asynccontextmanager
            async def lifespan(
                app: FastAPI
            ):
                # Setup code here
                yield
                # Teardown code here

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @asynccontextmanager
            async def lifespan(
                app: Litestar
            ):
                # Setup code here
                yield
                # Teardown code here


Cookies
~~~~~~~

While with FastAPI you usually set cookies on the response ``Response`` object, in Litestar there are two options: At the decorator level, using the ``response_cookies`` keyword argument, or dynamically at the response level (see: :ref:`Setting Cookies dynamically <usage/responses:setting cookies dynamically>`)

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/")
            async def index(response: Response) -> dict[str, str]:
                response.set_cookie(key="my_cookie", value="cookie_value")
                ...

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @get(response_cookies={"my-cookie": "cookie-value"})
            async def handler() -> str:
                ...


Dependencies parameters
~~~~~~~~~~~~~~~~~~~~~~~
The way dependencies parameters are passed differs between FastAPI and Litestar, note the `state: State` parameter in the Litestar example.
You can get the state either with the state kwarg in the handler or ``request.state`` (which point to the same object, a request local state, inherited from the application's state), or via `request.app.state`, the application's state.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Request

            async def get_arqredis(request: Request) -> ArqRedis:
                return request.state.arqredis

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import State

            async def get_arqredis(state: State) -> ArqRedis:
                return state.arqredis

Post json
~~~~~~~~~

In FastAPI, you pass the JSON object directly as a parameter to the endpoint, which will then be validated by Pydantic. In Litestar, you use the `data` keyword argument. The data will be parsed and validated by the associated modelling library.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python


            class ObjectType(BaseModel):
                name: str

            @app.post("/items/")
            async def create_item(object_name: ObjectType) -> dict[str, str]:
                return {"name": object_name.name}

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, post
            from pydantic import BaseModel

            class ObjectType(BaseModel):
                name: str

            @post("/items/")
            async def create_item(data: ObjectType) -> dict[str, str]:
                return {"name": data.name}


Default status codes
~~~~~~~~~~~~~~~~~~~~

Post defaults to 200 in FastApi and 201 in Litestar.

Templates
~~~~~~~~~

In FastAPI, you use `TemplateResponse` to render templates. In Litestar, you use the `Template` class.
Also FastAPI let you pass a dictionary while in Litestar you need to explicitly pass the context kwarg.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/uploads")
            async def get_uploads(request: Request):
                return templates.TemplateResponse(
                    "uploads.html", {"request": request, "debug": app.state.debug}
                )

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @get("/uploads")
            async def get_uploads(app_settings) -> Template:
                return Template(
                    name="uploads.html", context={"debug": app_settings.debug}
                )

Uploads
~~~~~~~

In FastAPI, you use the `File` class to handle file uploads. In Litestar, you use the `data` keyword argument with `Body` and specify the `media_type` as `RequestEncodingType.MULTI_PART`.
While this is more verbose, it's also more explicit and communicates the intent more clearly.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.post("/upload/")
            async def upload_file(files: list[UploadFile] = File(...)) -> dict[str, str]:
                return {"file_names": [file.filename for file in files]}

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @post("/upload/")
            async def upload_file(data: Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)]) -> dict[str, str]:
                return {"file_names": [file.filename for file in data]}

            app = Litestar([upload_file])


Exceptions signature
~~~~~~~~~~~~~~~~~~~~

In FastAPI, status code and exception details can be passed to `HTTPException` as positional arguments, while in Litestar they are set with keywords arguments, e.g. `status_code`. Positional arguments to `HTTPException` in Litestar will be added to the exception detail.
If migrating you just change your HTTPException import this will break.

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI, HTTPException

            app = FastAPI()

            @app.get("/")
            async def index() -> None:
                response_fields = {"array": "value"}
                raise HTTPException(
                    400, detail=f"can't get that field: {response_fields.get('array')}"
                )

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.exceptions import HTTPException

            @get("/")
            async def index() -> None:
                response_fields = {"array": "value"}
                raise HTTPException(
                    status_code=400, detail=f"can't get that field: {response_fields.get('array')}"
                )

            app = Litestar([index])


Authentication
~~~~~~~~~~~~~~

FastAPI promotes a pattern of using dependency injection for authentication. You can do the same in Litestar, but the
preferred way of handling this is extending :doc:`/usage/security/abstract-authentication-middleware`.

.. tab-set::
    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI, Depends, Request


            async def authenticate(request: Request) -> None: ...


            app = FastAPI()


            @app.get("/", dependencies=[Depends(authenticate)])
            async def index() -> dict[str, str]: ...


    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get, ASGIConnection, BaseRouteHandler


            async def authenticate(
                connection: ASGIConnection, route_handler: BaseRouteHandler
            ) -> None: ...


            @get("/", guards=[authenticate])
            async def index() -> dict[str, str]: ...


..  seealso::

    To learn more about security and authentication, check out this chapter in the
    documentation:

    * :doc:`/usage/security/index`

Dependency overrides
~~~~~~~~~~~~~~~~~~~~

While FastAPI includes a mechanism to override dependencies on an existing application object,
Litestar promotes architectural solutions to the issue this is aimed to solve. Therefore, overriding
dependencies in Litestar is strictly supported at definition time, i.e. when you’re defining
handlers, controllers, routers, and applications. Dependency overrides are fundamentally
the same idea as mocking and should be approached with the same caution and used sparingly
instead of being the default.

To achieve the same effect there are three general approaches:

1. Structuring the application with different environments in mind. This could mean for example
   connecting to a different database depending on the environment, which in turn is set via
   and env-variable. This is sufficient and most cases and designing your application around this
   principle is a general good practice since it facilitates configurability and integration-testing
   capabilities
2. Isolating tests for unit testing and using ``create_test_client``
3. Resort to mocking if none of the above approaches can be made to work

Middleware
~~~~~~~~~~

Pure ASGI middleware is fully compatible, and can be used with any ASGI framework. Middlewares
that make use of FastAPI/Starlette specific middleware features such as
Starlette’s `BaseHTTPMiddleware <https://www.starlette.io/middleware/#basehttpmiddleware>`_ are not compatible,
but can be easily replaced by :doc:`Creating Middlewares </usage/middleware/creating-middleware>`.
