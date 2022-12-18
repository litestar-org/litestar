# Migration to Starlite

Migrating **from either Starlette or FastAPI** to Starlite is rather uncomplicated, because the frameworks are for the
most
part **inter-compatible**. So what does need to be changed?

## From Starlette / FastAPI

### Routing Decorators

Starlite does not include any decorator as part of the `Router` or `Starlite` instances. **All routes have to be
declared
using [route handlers](usage/2-route-handlers/1-http-route-handlers.md)** – in standalone functions or controller
methods. You then have to
register them with the app, either by first **registering them on a router** and then **registering the router on the
app**, or
by **registering them directly on the app**. See
the [registering routes](usage/1-routing/1-registering-routes.md) part of the documentation for details.

=== "FastAPI"
    ```python
    from fastapi import FastAPI

    app = FastAPI()
    
    @app.get("/")
    async def index() -> dict[str, str]:
        ...
    ```

=== "Starlette"
    ```python
    from starlette.applications import Starlette
    from starlette.routing import Route

    async def index(request):
        ...

    routes = [Route("/", endpoint=index)]
    
    app = Starlette(routes=routes)
    ```

=== "Starlite"

    ```python
    from starlite import Starlite, get
    
    
    @get("/")
    async def index() -> dict[str, str]:
        ...
    
    app = Starlite([get])
    ```

### Routers and Routes

There are a few key differences between Starlite's and Starlette's `Router` class:

1. The Starlite version is not an ASGI app
2. The Starlite version does not include decorators: Use [route handlers](usage/2-route-handlers/1-http-route-handlers.md).
3. The Starlite version does not support lifecycle hooks: Those have to be handled on the application layer. See [lifecycle hooks](usage/13-lifecycle-hooks/)

If you are using Starlette's `Route`s, you will need to replace these with [route handlers](usage/2-route-handlers/1-http-route-handlers.md).

### Host based routing

Host based routing class is intentionally unsupported. If your application relies on `Host` you will have to separate
the logic into different services and handle this part of request dispatching with a proxy server like [nginx](https://www.nginx.com/)
or [traefik](https://traefik.io/).

### Dependency Injection

The Starlite dependency injection system is different from the one used by FastAPI. You can read about it in
the [dependency injection](usage/6-dependency-injection/0-dependency-injection-intro.md) section of the documentation.

In FastAPI you declare dependencies either as a list of functions passed to the `Router` or `FastAPI` instances, or as a
default function argument value wrapped in an instance of the `Depends` class.

In Starlite **dependencies are always declared using a dictionary** with a string key and the value wrapped in an
instance of the `Provide` class. This also allows to transparently override dependencies on every level of the application,
and to easily access dependencies from higher levels.

=== "FastAPI"

    ```python
    from fastapi import FastAPI, Depends, APIRouter
    
    
    async def route_dependency() -> bool:
        ...
    
    
    async def nested_dependency() -> str:
        ...
    
    
    async def router_dependency() -> int:
        ...
    
    
    async def app_dependency(data: str = Depends(nested_dependency)) -> int:
        ...
    
    
    router = APIRouter(dependencies=[Depends(router_dependency)])
    app = FastAPI(dependencies=[Depends(nested_dependency)])
    app.include_router(router)
    
    
    @app.get("/")
    async def handler(
            val_route: bool = Depends(route_dependency),
            val_router: int = Depends(router_dependency),
            val_nested: str = Depends(nested_dependency),
            val_app: int = Depends(app_dependency),
    ) -> None:
        ...
    ```

=== "Starlite"

    ```python
    from starlite import Starlite, Provide, get, Router

    async def route_dependency() -> bool:
        ...
    
    async def nested_dependency() -> str:
        ...
    
    async def router_dependency() -> int:
        ...
    
    async def app_dependency(nested: str) -> int:
        ...
    
    @get("/", dependencies={"val_route": Provide(route_dependency)})
    async def handler(
            val_route: bool, 
            val_router: int, 
            val_nested: str, 
            val_app: int
    ) -> None:
        ...
    
    router = Router(dependencies={"val_router": Provide(router_dependency)})
    app = Starlite(
        route_handlers=[handler], 
        dependencies={
            "val_app": Provide(app_dependency), 
            "val_nested": Provide(nested_dependency)
        }
    )
    ```

#### Authentication

FastAPI promotes a pattern of using dependency injection for authentication. You can do the same in Starlite, but the
preferred way of handling this
is extending [`AbstractAuthenticationMiddleware`](usage/8-security/0-intro.md).

=== "FastAPI"
    ```python
    from fastapi import FastAPI, Depends, Request

    async def authenticate(request: Request) -> None:
        ...
    
    app = FastAPI()
    
    @app.get("/", dependencies=[Depends(authenticate)])
    async def index() -> dict[str, str]:
        ...
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get, ASGIConnection, BaseRouteHandler

    async def authenticate(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        ...
    
    @get("/", guards=[authenticate])
    async def index() -> dict[str, str]:
        ...
    ```

### Middleware

Pure ASGI middleware is fully compatible, and can be used with any ASGI framework. Middlewares
that make use of FastAPI/Starlette specific middleware features such as 
Starlette's [`BaseHTTPMiddleware`](https://www.starlette.io/middleware/#basehttpmiddleware) are not compatible,
but can be easily replaced by making use of [`AbstractMiddleware`](usage/7-middleware/2-creating-middleware/2-using-abstract-middleware/)