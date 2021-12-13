# The Starlite App

At the root of every starlite application is an instance of the `Starlite` class or a subclass of it:

Instantiating the app is straightforward:

```python
from starlite import Starlite

app = Starlite()
```

The `Starlite` class supports the following (optional) kwargs:

* `debug`: a boolean flag toggling debug mode on and off
* `middleware`: a sequence of `Middleware` subclasses
* `exception_handlers`: a dictionary mapping exceptions or exception codes to callables
* `route_handlers`: a sequence of route handlers
* `on_startup`: a sequence of callables to be called during the application startup
* `on_shutdown`: a sequence of callables to be called during the application shutdown
* `lifespan`: an async-context that handles startup and shutdown
* `dependencies`: a dictionary mapping keys to dependency providers
* `logging_config`: either a subclass of `starlite.logging.LoggingConfig` or None (disable logging)

> :warning: **Warning**: debug should not be used in production
> :warning: **Warning**: you can specify either `on_startup`/`on_shutdown` or `lifespan` but not both
