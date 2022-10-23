# CORS

CORS ([Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)) is a common security
mechanism - that is often implemented using middleware. To enable CORS in a starlite application simply pass an instance
of [`CORSConfig`][starlite.config.CORSConfig] to the [Starlite constructor][starlite.app.Starlite]:

```python
from starlite import CORSConfig, Starlite

cors_config = CORSConfig(allow_origins=["https://www.example.com"])

app = Starlite(route_handlers=[...], cors_config=cors_config)
```

See the [API Reference][starlite.config.CORSConfig] for full details on the `CORSConfig` class and the kwargs it accepts.

!!! note
    The asterisks symbol in the above kwargs means "match any".

You can read more about this middleware in the [starlette docs](https://www.starlette.io/middleware/#corsmiddleware).
