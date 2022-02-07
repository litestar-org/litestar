# Migration to Starlite

Migrating **from either Starlette or FastAPI** to Starlite is rather uncomplicated, because the frameworks are for the most
part **inter-compatible**. So what does need to be changed?

### LifeCycle

If you use the **Starlette/FastAPI `lifecycle` kwarg** with an **`AsyncContextManager`** to bootstrap your application, you will
need to convert it to use the **`on_startup` and `on_shutdown` [hooks](usage/0-the-starlite-app.md#startup-and-shutdown)**. Otherwise, using lifecycle management is identical.

### Routing Decorators

Starlite does not include any decorator as part of the `Router` or `Starlite` instances. **All routes have to be declared
using [route handlers](usage/2-route-handlers/1_http_route_handlers.md)** – in standalone functions or Controller methods. You then have to
register them with the app, either by first **registering them on a router** and then **registering the router on the app**, or
by **registering them directly on the app**. See
the [registering routes](usage/1-routers-and-controllers.md#registering-routes) part of the documentation for details.

### Routing Classes

As discussed in the [relation to starlette routing](usage/1-routers-and-controllers.md#relation-to-starlette-routing)
section of the documentation, Starlite **does not extend the Starlette routing classes** and instead implements its own
versions of these. You will **need to use the Starlite `Router` classes** instead of their equivalents from the other
frameworks. There are some **differences** from the **Starlite class** to those from the other frameworks:

1. The Starlite version is **not an ASGI app**, the only ASGI app is the Starlite app and any middlewares you pass to it.
2. The Starlite version **does not include decorators**, instead you have to use [route handlers](usage/2-route-handlers/1_http_route_handlers.md).
3. The Starlite version **does not support lifecycle** hooks, instead you have to handle all of your lifecycle management in
   the app layer.

If you use the Starlette `Route` instances directly, you will need to replace these
with [route handlers](usage/2-route-handlers/1_http_route_handlers.md).

<!-- prettier-ignore -->
!!! important
    The Starlette `Mount` class is replaced by the Starlite `Router`. The `Host` class is intentionally
    unsupported. If your application relies on `Host` you will have to separate the logic into different microservices
    rather than use this kind of routing

### Dependency Injection

The Starlite dependency injection system is different from the one used by FastAPI. You can read about it in
the [dependency injection](usage/6-dependency-injection.md) section of the documentation.

In FastAPI you declare dependencies either as a list of functions passed to the `Router` or `FastAPI` instances, or as a
default function argument value wrapped in an instance of the `Depend` class.

In Starlite **dependencies are always declared using a dictionary** with a string key and the value wrapped in an instance of
the `Provide` class.

### Authentication

FastAPI promotes a pattern of using dependency injection for authentication. You can do the same in Starlite, but the
preferred way of handling this
is [extending the Starlite AbstractAuthenticationMiddleware class](usage/8-authentication.md).

### Third Party Packages

Third party packages created for **Starlette** and **FastAPI** should be **generally compatible** with Starlite. The only
**exceptions** are for packages that use the **FastAPI dependency injection** system as a basis - these will not work as such.
