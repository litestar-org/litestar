# Response Headers

Starlite allows you to define response headers by using the `response_headers` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers and the app
itself:

```python
--8<-- "examples/responses/response_headers.py"
```

In the above example the response returned from `my_route_handler` will have headers set from each layer of the
application using the given key+value combinations. I.e. it will be a dictionary equal to this:

```json
{
  "my-local-header": "local header",
  "controller-level-header": "controller header",
  "router-level-header": "router header",
  "app-level-header": "app header"
}
```

The respective descriptions will be used for the OpenAPI documentation.

## Dynamic Headers

The above detailed scheme works great for statically configured headers, but how would you go about handling dynamically
setting headers? Starlite allows you to set headers dynamically in several ways and below we will detail the two
primary patterns.

### Setting Response Headers Using Annotated Responses

We can simply return a response instance directly from the route handler and set the headers dictionary manually
as you see fit, e.g.:

```python
--8<-- "examples/responses/response_headers_2.py"
```

In the above we use the `response_headers` kwarg to pass the `name` and `description` parameters for the `Random-Header`
to the OpenAPI documentation, but we set the value dynamically in as part of
the [annotated response](3-returning-responses.md#annotated-responses) we return. To this end we do not set a `value`
for it and we designate it as `documentation_only=True`.

### Setting Response Headers Using the After Request Hook

An alternative pattern would be to use an [after request handler](../13-lifecycle-hooks.md#after-request). We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the headers on the corresponding layer:

```python
--8<-- "examples/response_headers_3.py"
```

In the above we set the response header using an `after_request_handler` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granularly by overriding header specification as
required. For example, lets say we have a router level header being set and a local header with the same key but a
different value range:

```python
--8<-- "examples/responses/response_headers_4.py"
```

## Specific Headers Implementation

Starlite has a dedicated implementation for a few headers that are commonly used. These headers can be set separately
with dedicated keyword arguments or as class attributes on all layers of the app (individual route handlers, controllers,
routers and the app itself). Each layer overrides the layer above it - thus, the headers defined for a specific route
handler will override those defined on its router, which will in turn override those defined on the app level.

These header implementations allow easy creating, serialization and parsing according to the associated header
specifications.

### Cache Control

[`CacheControlHeader`][starlite.datastructures.CacheControlHeader] represents a
[`Cache-Control` Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control).

Here is a simple example that shows how to use it:

```py title="Cache Control Header"
--8<-- "examples/datastructures/headers/cache_control.py"
```

In this example we have a `cache-control` with `max-age` of 1 month for the whole app, a `max-age` of
1 day for all routes within `MyController` and `no-store` for one specific route `get_server_time`. Here are the cache
control values that will be returned from each endpoint:

- When calling `/population` the response will have `cache-control` with `max-age=2628288` (1 month).
- When calling `/chance_of_rain` the response will have `cache-control` with `max-age=86400` (1 day).
- When calling `/timestamp` the response will have `cache-control` with `no-store` which means don't store the result
in any cache.

### ETag

[`ETag`][starlite.datastructures.ETag] represents an
[`ETag` header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag).

Here are some usage examples:

```py title="Returning ETag headers"
--8<-- "examples/datastructures/headers/etag.py"
```

```py title="Parsing ETag heaers"
--8<-- "examples/datastructures/headers/etag_parsing.py"
```
