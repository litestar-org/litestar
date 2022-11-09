# Response Cookies

Starlite allows you to define response cookies by using the `response_cookies` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers and the app
itself:

```python
--8 < --"examples/response_cookies_1.py"
```

In the above example, the response returned by `my_route_handler` will have cookies set by each layer of the
application. Cookies are set using
the [Set-Cookie header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie) and with above resulting
in:

```text
Set-Cookie: local-cookie=local value; Path=/; SameSite=lax
Set-Cookie: controller-cookie=controller value; Path=/; SameSite=lax
Set-Cookie: router-cookie=router value; Path=/; SameSite=lax
Set-Cookie: app-cookie=app value; Path=/; SameSite=lax
```

You can easily override cookies declared in higher levels by re-declaring a cookie with the same key in a lower level,
e.g.:

```python
--8 < --"examples/responses/response_cookies.py"
```

Of the two declarations of `my-cookie` only the route handler one will be used, because its lower level:

```text
Set-Cookie: my-cookie=456; Path=/; SameSite=lax
```

## The Cookie Class

Starlite exports the class `starlite.datastructures.Cookie`. This is a pydantic model that allows you to define
a cookie. See the [API Reference][starlite.datastructures.Cookie] for full details on the `Cookie` class and the kwargs it accepts.

## Dynamic Cookies

While the above scheme works great for static cookie values, it doesn't allow for dynamic cookies. Because cookies are
fundamentally a type of response header, we can utilize the same patterns we use for
setting [dynamic headers](./4-response-headers.md#dynamic-headers) also here.

### Setting Response Cookies Using Annotated Responses

We can simply return a response instance directly from the route handler and set the cookies list manually
as you see fit, e.g.:

```python
--8 < --"examples/response_cookies_3.py"
```

In the above we use the `response_cookies` kwarg to pass the `key` and `description` parameters for the `Random-Header`
to the OpenAPI documentation, but we set the value dynamically in as part of
the [annotated response](3-returning-responses.md#annotated-responses) we return. To this end we do not set a `value`
for it and we designate it as `documentation_only=True`.

### Setting Response Cookies Using the After Request Hook

An alternative pattern would be to use an [after request handler](../13-lifecycle-hooks.md#after-request). We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the cookies on the corresponding layer:

```python
--8 < --"examples/response_cookies_4.py"
```

In the above we set the cookie using an `after_request_handler` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granularly by overriding cookie specification as
required. For example, lets say we have a router level cookie being set and a local cookie with the same key but a
different value range:

```python
--8 < --"examples/response_cookies_5.py"
```
