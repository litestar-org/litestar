# CORS

CORS ([Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)) is a common security
mechanism - that is often implemented using middleware. To enable CORS in a starlite application simply pass an instance
of `starlite.config.CORSConfig` to the Starlite constructor:

```python
from starlite import CORSConfig, Starlite

cors_config = CORSConfig(allow_origins=["https://www.example.com"])

app = Starlite(route_handlers=[...], cors_config=cors_config)
```

You can pass the following kwargs to CORSConfig:

- `allow_origins`: list of domain schemas, defaults to `["*"]`
- `allow_methods`: list of http methods, defaults to `["*"]`
- `allow_headers`: list of header keys, defaults to `["*"]`
- `allow_credentials`: A boolean dictating whether CORS should support cookies in cross-origin requests. Defaults
  to `False`.
- `allow_origin_regex`: A regex string that is matches against incoming request origins. Defaults to `None`.
- `expose_headers`: A list of response headers to expose. Defaults to `[]`.
- `max_age`: Sets a response header instructing the max amount of _seconds_ that the browser should cache a CORS
  response. Defaults to 600.

!!! note
    The asterisks symbol in the above kwargs means "match any".

You can read more about this middleware in the [starlette docs](https://www.starlette.io/middleware/#corsmiddleware).
