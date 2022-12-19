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
        val_route: bool, val_router: int, val_nested: str, val_app: int
    ) -> None:
        ...


    router = Router(dependencies={"val_router": Provide(router_dependency)})
    app = Starlite(
        route_handlers=[handler],
        dependencies={
            "val_app": Provide(app_dependency),
            "val_nested": Provide(nested_dependency),
        },
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


    async def authenticate(
        connection: ASGIConnection, route_handler: BaseRouteHandler
    ) -> None:
        ...


    @get("/", guards=[authenticate])
    async def index() -> dict[str, str]:
        ...
    ```


#### Dependency overrides

While FastAPI includes a mechanism to override dependencies on an existing application object,
Starlite promotes architecular solutions to the issue this is aimed to solve. Therefore, overriding 
dependencies in Starlite is strictly supported at definition time, i.e. when you're defining
handlers, controllers, routers and applications. Dependency overrides are fundamentally 
the same idea as mocking and should be approached with the same caution and used sparingly 
instead of being the default.

To achieve the same effect there are three general approaches:

1. Structuring the application with different environments in mind. This could mean for example 
   connecting to a different database depending on the environment, which in turn is set via
   and env-variable. This is sufficient and most cases and designing your application around this
   principle is a general good practice since it facilitates configurability and integration-testing
   capabilities
2. Isolating tests for unit testing and using `create_test_client`
3. Resort to mocking if none of the above approaches can be made to work


### Middleware

Pure ASGI middleware is fully compatible, and can be used with any ASGI framework. Middlewares
that make use of FastAPI/Starlette specific middleware features such as
Starlette's [`BaseHTTPMiddleware`](https://www.starlette.io/middleware/#basehttpmiddleware) are not compatible,
but can be easily replaced by making use of [`AbstractMiddleware`](usage/7-middleware/2-creating-middleware/2-using-abstract-middleware/)


## From Flask

### Routing

=== "Flask"
    ```python
    from flask import Flask

    app = Flask(__name__)


    @app.route("/")
    def index():
        return "Index Page"


    @app.route("/hello")
    def hello():
        return "Hello, World"
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get


    @get("/")
    def index() -> str:
        return "Index Page"


    @get("/hello")
    def hello() -> str:
        return "Hello, World"


    app = Starlite([index, hello])
    ```

#### Path parameters

=== "Flask"
    ```python
    from flask import Flask

    app = Flask(__name__)


    @app.route("/user/<username>")
    def show_user_profile(username):
        return f"User {username}"


    @app.route("/post/<int:post_id>")
    def show_post(post_id):
        return f"Post {post_id}"


    @app.route("/path/<path:subpath>")
    def show_subpath(subpath):
        return f"Subpath {subpath}"
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get
    from pathlib import Path


    @get("/user/{username:str}")
    def show_user_profile(username: str) -> str:
        return f"User {username}"


    @get("/post/{post_id:int}")
    def show_post(post_id: int) -> str:
        return f"Post {post_id}"


    @get("/path/{subpath:path}")
    def show_subpath(subpath: Path) -> str:
        return f"Subpath {subpath}"


    app = Starlite([show_user_profile, show_post, show_subpath])
    ```

### Request object

In Flask, the current request can be accessed through a global `request` variable. In Starlite,
the request can be accessed through an optional parameter in the handler function.

=== "Flask"
    ```python
    from flask import Flask, request

    app = Flask(__name__)


    @app.get("/")
    def index():
        print(request.args)
    ```


=== "Starlite"
    ```python
    from starlite import Starlite, get, Request


    @get("/")
    def index(request: Request) -> None:
        print(request.query_params)
    ```

### Templates

Flask comes with the [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templating
engine built-in. You can use Jinja with Starlite as well, but you'll need to install it
explicitly. You can do by installing Starlite with `pip install starlite[jinja]`.
In addition to Jinja, Starlite supports [Mako](https://www.makotemplates.org/) templates as well.

=== "Flask"
    ```python
    from flask import Flask, render_template

    app = Flask(__name__)


    @app.route("/hello/<name>")
    def hello(name):
        return render_template("hello.html", name=name)
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get, TemplateConfig, Template
    from starlite.contrib.jinja import JinjaTemplateEngine


    @get("/hello/{name:str}")
    def hello(name: str) -> Template:
        return Template(name="hello.html", context={"name": name})


    app = Starlite(
        [hello],
        template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
    )
    ```
