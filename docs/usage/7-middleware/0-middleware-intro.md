# Introduction

Middlewares in Starlite are ASGI apps that are called "in the middle" between the application entrypoint and the
route handler function.

Starlite ships with several builtin middlewares (some coming from Starlette) that are easy to configure and use.
See [the documentation regarding these](./3-builtin-middlewares/0-builtin-middlewares-intro.md) for more details.

You can also use the builtin [Starlette Middlewares](https://www.starlette.io/middleware/) and most 3rd party middlewares
created for Starlette or FastAPI.

!!! note
3rd party middlewares for Starlette that rely on the Starlette routing system are incompatible with Starlite.
To understand why, read about [the Starlite routing system](../1-routing/0-routing.md).
