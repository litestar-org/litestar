# Introduction

Middlewares in Starlite are ASGI apps that are called "in the middle" between the application entrypoint and the
route handler function.

Starlite ships with several builtin middlewares that are easy to configure and use.
See [the documentation regarding these](builtin-middlewares) for more details.


!!! info
    If you're coming from Starlette / FastAPI, take a look at the
    [section on middleware](/starlite/migration/#middleware) in the migration guide.
