# The Starlite App

At the root of every Starlite application is an **instance** of the [`Starlite`][starlite.app.Starlite] class or a
subclass of it.

Typically, this code will be placed in a file called `main.py` at the **project's root directory**.

Creating an app is straightforward – the **only required arg is a list**
of [Controllers](../1-routing/3-controllers.md#controllers), [Routers](../1-routing/2-routers.md)
or [Route Handlers](../2-route-handlers/1-http-route-handlers.md):

!!! important
    This example requires Python 3.9 or later.

```py title="Hello World"
--8<-- "examples/hello_world.py"
```

The **app instance is the root level** of the app - it has the base path of `/` and all root level Controllers, Routers
and Route Handlers should be registered on it. See [registering routes](../1-routing/1-registering-routes.md) for
full details.

See the [API Reference][starlite.app.Starlite] for full details on the Starlite class and the kwargs it accepts.
