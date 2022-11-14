# Mounting ASGI Apps

Starlite support "mounting" ASGI applications on sub paths, that is - specifying a handler function that will handle all
requests addressed to a given path.

```py title="Mounting an ASGI App"
--8<-- "examples/routing/mount_custom_app.py"
```

The handler function will receive all requests with an url that begins with `/some/sub-path`, e.g. `/some/sub-path` and
`/some/sub-path/abc` and `/some/sub-path/123/another/sub-path` etc.

!!! info Technical Details
    If we are sending a request to the above with the url `/some/sub-path`, the handler will be invoked and
    the value of `scope["path"]` will equal `/`. If we send a request to `/some/sub-path/abc`, it will also be invoked,
    and `scope["path"]` will equal `/abc`.

Mounting is especially useful when you need to combine components of other ASGI applications - for example, for 3rd part libraries.
The following example is identical in principle to the one above, but it uses `Starlette`:

```py title="Mounting a Starlette App"
--8<-- "examples/routing/mounting_starlette_app.py"
```
