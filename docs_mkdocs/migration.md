# Migrating to Starlite

Migrating from [Starlette](https://www.starlette.io/) or
[FastAPI](https://fastapi.tiangolo.com/) to Starlite is straightforward, as they are both
ASGI frameworks and as such build on the same fundamental principles. The following sections
can help to navigate a migration from either framework by introducing Starlite-equivalents
to common functionalities.

## From Starlette / FastAPI

### Routing Decorators

Starlite does not include any decorator as part of the `Router` or `Starlite` instances.
Instead, all routes are declared using [route handlers](usage/2-route-handlers/1-http-route-handlers.md),
either as standalone functions or controller methods. The handler can then be registered
on an application or router instance.

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

!!! info "Learn more"
    To learn more about registering routes, check out this chapter
    in the documentation: [registering routes](usage/1-routing/1-registering-routes.md)


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


!!! info "Learn more"
    To learn more about dependency injection, check out this chapter
    in the documentation: [Dependency injection](usage/6-dependency-injection/0-dependency-injection-intro/)


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


!!! info "Learn more"
    To learn more about security and authentication, check out this chapter in the
    documentation: [Security](usage/8-security/0-intro/)


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

### ASGI vs WSGI

[Flask](https://flask.palletsprojects.com) is a WSGI framework, whereas Starlite
is built using the modern [ASGI](https://asgi.readthedocs.io) standard. A key difference
is that *ASGI* is built with async in mind.

While Flask has added support for `async/await`, it remains synchronous at its core;
The async support in Flask is limited to individual endpoints.
What this means is that while you can use `async def` to define endpoints in Flask,
**they will not run concurrently** - requests will still be processed one at a time.
Flask handles asynchronous endpoints by creating an event loop for each request, run the
endpoint function in it and then return its result.

ASGI on the other hand does the exact opposite; It runs everything in a central event loop.
Starlite then adds support for synchronous functions by running them in a non-blocking way
*on the event loop*. What this means is that synchronous and asynchronous code both run
concurrently.

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


!!! info "Learn more"
    To learn more about path parameters, check out this chapter
    in the documentation: [Path parameters](usage/3-parameters/0-path-parameters/)


### Request object

In Flask, the current request can be accessed through a global `request` variable. In Starlite,
the request can be accessed through an optional parameter in the handler function.

=== "Flask"
    ```python
    from flask import Flask, request

    app = Flask(__name__)


    @app.get("/")
    def index():
        print(request.method)
    ```


=== "Starlite"
    ```python
    from starlite import Starlite, get, Request


    @get("/")
    def index(request: Request) -> None:
        print(request.method)
    ```

#### Request methods

| Flask                         | Starlite                                                                                   |
|-------------------------------|--------------------------------------------------------------------------------------------|
| `request.args`                | `request.query_params`                                                                     |
| `request.base_url`            | `request.base_url`                                                                         |
| `request.authorization`       | `request.auth`                                                                             |
| `request.cache_control`       | `request.headers.get("cache-control")`                                                     |
| `request.content_encoding`    | `request.headers.get("content-encoding")`                                                  |
| `request.content_length`      | `request.headers.get("content-length")`                                                    |
| `request.content_md5`         | -                                                                                          |
| `request.content_type`        | `request.content_type`                                                                     |
| `request.cookies`             | `request.cookies`                                                                          |
| `request.data`                | `request.body()`                                                                           |
| `request.date`                | `request.headers.get("date")`                                                              |
| `request.endpoint`            | `request.route_handler`                                                                    |
| `request.environ`             | `request.scope`                                                                            |
| `request.files`               | Use [`UploadFile`](usage/4-request-data/#file-uploads)                                     |
| `request.form`                | `request.form()`, prefer [`Body`](usage/4-request-data/#specifying-a-content-type)         |
| `request.get_json`            | `request.json()`, prefer the [`data keyword argument`](usage/4-request-data/#request-body) |
| `request.headers`             | `request.headers`                                                                          |
| `request.host`                | -                                                                                          |
| `request.host_url`            | -                                                                                          |
| `request.if_match`            | `request.headers.get("if-match")`                                                          |
| `request.if_modified_since`   | `request.headers.get("if_modified_since")`                                                 |
| `request.if_none_match`       | `request.headers.get("if_none_match")`                                                     |
| `request.if_range`            | `request.headers.get("if_range")`                                                          |
| `request.if_unmodified_since` | `request.headers.get("if_unmodified_since")`                                               |
| `request.method`              | `request.method`                                                                           |
| `request.mimetype`            | -                                                                                          |
| `request.mimetype_params`     | -                                                                                          |
| `request.origin`              | -                                                                                          |
| `request.path`                | `request.scope["path"]`                                                                    |
| `request.query_string`        | `request.scope["query_string"]`                                                            |
| `request.range`               | `request.headers.get("range")`                                                             |
| `request.referrer`            | `request.headers.get("referrer")`                                                          |
| `request.remote_addr`         | -                                                                                          |
| `request.remote_user`         | -                                                                                          |
| `request.root_path`           | `request.scope["root_path"]`                                                               |
| `request.server`              | `request.scope["server"]`                                                                  |
| `request.stream`              | `request.stream`                                                                           |
| `request.url`                 | `request.url`                                                                              |
| `request.url_charset`         | -                                                                                          |
| `request.user_agent`          | `request.headers.get("user-agent")`                                                        |
| `request.user_agent`          | `request.headers.get("user-agent")`                                                        |


!!! info "Read more"
    To learn more about requests,, check out these chapters in the documentation:

    - [Request data](usage/4-request-data/)
    - [Request reference](reference/connection/1-request/)


### Static files

Like Flask, Starlite also has capabilities for serving static files, but while Flask
will automatically serve files from a `static` folder, this has to be configured explicitly
in Starlite.

```python
from starlite import Starlite, StaticFilesConfig

app = Starlite(
    [], static_files_config=StaticFilesConfig(path="/static", directories=["static"])
)
```

!!! info "Read more"
    To learn more about static files, check out this chapter in the documentation:
    [Static files](usage/0-the-starlite-app/3-static-files/)


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

!!! info "Read more"
    To learn more about templates, check out this chapter in the documentation:
    [Template engines](usage/16-templating/0-template-engines/)


### Setting cookies and headers

=== "Flask"
    ```python
    from flask import Flask, make_response

    app = Flask(__name__)


    @app.get("/")
    def index():
        response = make_response("hello")
        response.set_cookie("my-cookie", "cookie-value")
        response.headers["my-header"] = "header-value"
        return response
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get, ResponseHeader, Cookie, Response


    @get(
        "/static",
        response_headers={"my-header": ResponseHeader(value="header-value")},
        response_cookies=[Cookie("my-cookie", "cookie-value")],
    )
    def static() -> str:
        # you can set headers and cookies when defining handlers
        ...


    @get("/dynamic")
    def dynamic() -> Response[str]:
        # or dynamically, by returning an instance of Response
        return Response(
            "hello",
            headers={"my-header": "header-value"},
            cookies=[Cookie("my-cookie", "cookie-value")],
        )
    ```

!!! info "Read more"
    To learn more about response headers and cookies, check out these chapters in the
    documentation:

    - [Response headers](/usage/5-responses/4-response-headers/)
    - [Response cookies](/usage/5-responses/5-response-cookies/)


### Redirects

For redirects, instead of `redirect` use `Redirect`:

=== "Flask"
    ```python
    from flask import Flask, redirect, url_for

    app = Flask(__name__)


    @app.get("/")
    def index():
        return "hello"


    @app.get("/hello")
    def hello():
        return redirect(url_for("index"))
    ```


=== "Starlite"
    ```python
    from starlite import Starlite, get, Redirect


    @get("/")
    def index() -> str:
        return "hello"


    @get("/hello")
    def hello() -> Redirect:
        return Redirect(path="index")


    app = Starlite([index, hello])
    ```

### Raising HTTP errors

Instead of using the `abort` function, raise an `HTTPException`:

=== "Flask"
    ```python
    from flask import Flask, abort

    app = Flask(__name__)


    @app.get("/")
    def index():
        abort(400, "this did not work")
    ```


=== "Starlite"
    ```python
    from starlite import Starlite, get, HTTPException


    @get("/")
    def index() -> None:
        raise HTTPException(status_code=400, detail="this did not work")


    app = Starlite([index])
    ```

!!! info "Learn more"
    To learn more about exceptions, check out this chapter in the documentation: [Exceptions](usage/17-exceptions)

### Setting status codes

=== "Flask"
    ```python
    from flask import Flask

    app = Flask(__name__)


    @app.get("/")
    def index():
        return "not found", 404
    ```


=== "Starlite"
    ```python
    from starlite import Starlite, get, Response


    @get("/static", status_code=404)
    def static_status() -> str:
        return "not found"


    @get("/dynamic")
    def dynamic_status() -> Response[str]:
        return Response("not found", status_code=404)


    app = Starlite([static_status, dynamic_status])
    ```


### Serialization

Flask uses a mix of explicit conversion (such as `jsonify`) and inference (i.e. the type
of the returned data) to determine how data should be serialized. Starlite instead assumes
the data returned is intended to be serialized into JSON and will do so unless told otherwise.

=== "Flask"
    ```python
    from flask import Flask, Response

    app = Flask(__name__)


    @app.get("/json")
    def get_json():
        return {"hello": "world"}


    @app.get("/text")
    def get_text():
        return "hello, world!"


    @app.get("/html")
    def get_html():
        return Response("<strong>hello, world</strong>", mimetype="text/html")
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, get, MediaType


    @get("/json")
    def get_json() -> dict[str, str]:
        return {"hello": "world"}


    @get("/text", media_type=MediaType.TEXT)
    def get_text() -> str:
        return "hello, world"


    @get("/html", media_type=MediaType.HTML)
    def get_html() -> str:
        return "<strong>hello, world</strong>"


    app = Starlite([get_json, get_text, get_html])
    ```


### Error handling

=== "Flask"
    ```python
    from flask import Flask
    from werkzeug.exceptions import HTTPException

    app = Flask(__name__)


    @app.errorhandler(HTTPException)
    def handle_exception(e):
        ...
    ```

=== "Starlite"
    ```python
    from starlite import Starlite, HTTPException, Request, Response


    def handle_exception(request: Request, exception: Exception) -> Response:
        ...


    app = Starlite([], exception_handlers={HTTPException: handle_exception})
    ```


!!! info "Learn more"
    To learn more about exception handling, check out this chapter in the documentation:
    [Exception handling](usage/17-exceptions/#exception-handling)
