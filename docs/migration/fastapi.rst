From Starlette / FastAPI
------------------------

Routing Decorators
~~~~~~~~~~~~~~~~~~

Starlite does not include any decorator as part of the ``Router`` or ``Starlite`` instances.
Instead, all routes are declared using :doc:`route handlers </usage/route-handlers>`, either as standalone functions or
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

    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

           from starlite import Starlite, get


           @get("/")
           async def index() -> dict[str, str]: ...


           app = Starlite([index])


..  seealso::

    To learn more about registering routes, check out this chapter
    in the documentation: :ref:`registering routes <usage/routing:registering routes>`

Routers and Routes
~~~~~~~~~~~~~~~~~~

There are a few key differences between Starlite’s and Starlette’s ``Router`` class:

1. The Starlite version is not an ASGI app
2. The Starlite version does not include decorators: Use :doc:`route handlers </usage/route-handlers>`.
3. The Starlite version does not support lifecycle hooks: Those have to be handled on the application layer. See :doc:`lifecycle hooks </usage/lifecycle-hooks>`

If you are using Starlette’s ``Route``\ s, you will need to replace these with :doc:`route handlers </usage/route-handlers>`.

Host based routing
~~~~~~~~~~~~~~~~~~

Host based routing class is intentionally unsupported. If your application relies on ``Host`` you will have to separate
the logic into different services and handle this part of request dispatching with a proxy server like `nginx <https://www.nginx.com/>`_
or `traefik <https://traefik.io/>`_.

Dependency Injection
~~~~~~~~~~~~~~~~~~~~

The Starlite dependency injection system is different from the one used by FastAPI. You can read about it in
the :doc:`dependency injection </usage/dependency-injection>` section of the documentation.

In FastAPI you declare dependencies either as a list of functions passed to the ``Router`` or ``FastAPI`` instances, or as a
default function argument value wrapped in an instance of the ``Depends`` class.

In Starlite **dependencies are always declared using a dictionary** with a string key and the value wrapped in an
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



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

           from starlite import Starlite, Provide, get, Router


           async def route_dependency() -> bool: ...


           async def nested_dependency() -> str: ...


           async def router_dependency() -> int: ...


           async def app_dependency(nested: str) -> int: ...


           @get("/", dependencies={"val_route": Provide(route_dependency)})
           async def handler(
               val_route: bool, val_router: int, val_nested: str, val_app: int
           ) -> None: ...


           router = Router(dependencies={"val_router": Provide(router_dependency)})
           app = Starlite(
               route_handlers=[handler],
               dependencies={
                   "val_app": Provide(app_dependency),
                   "val_nested": Provide(nested_dependency),
               },
           )


..  seealso::

    To learn more about dependency injection, check out this chapter
    in the documentation: `Dependency injection <usage/6-dependency-injection/0-dependency-injection-intro/>`__

Authentication
^^^^^^^^^^^^^^

FastAPI promotes a pattern of using dependency injection for authentication. You can do the same in Starlite, but the
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


    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, ASGIConnection, BaseRouteHandler


            async def authenticate(
                connection: ASGIConnection, route_handler: BaseRouteHandler
            ) -> None: ...


            @get("/", guards=[authenticate])
            async def index() -> dict[str, str]: ...


..  seealso::

    To learn more about security and authentication, check out this chapter in the
    documentation: `Security <usage/8-security/0-intro/>`_

Dependency overrides
^^^^^^^^^^^^^^^^^^^^

While FastAPI includes a mechanism to override dependencies on an existing application object,
Starlite promotes architectural solutions to the issue this is aimed to solve. Therefore, overriding
dependencies in Starlite is strictly supported at definition time, i.e. when you’re defining
handlers, controllers, routers and applications. Dependency overrides are fundamentally
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
but can be easily replaced by making use of `AbstractMiddleware
<usage/7-middleware/2-creating-middleware/2-using-abstract-middleware/>`_
