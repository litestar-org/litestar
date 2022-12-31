# Introduction

Middlewares in Starlite are ASGI apps that are called "in the middle" between the application entrypoint and the
route handler function.

Starlite ships with several builtin middlewares (some coming from Starlette) that are easy to configure and use.
See [the documentation regarding these](builtin-middlewares) for more details.

You can also use the builtin [Starlette Middlewares](https://www.starlette.io/middleware/) and most 3rd party middlewares
created for Starlette or FastAPI.

!!! info
    If you're coming from Starlette and use middleware that interacts with Starlette's routing
    system, this middleware will not work in Starlite. To understand why,
    read about [the Starlite routing system](../1-routing/0-routing.md).
