# Mounting ASGI Apps

Starlite support "mounting" ASGI applications on sub paths, that is - specifying a handler function that will have all
requests addressed to a given path or a sub-path of that path.

```py title="Mounting an ASGI App"
--8<-- "examples/routing/mounting.py"
```

The handler function will receive all requests with a url that begins with `/some/sub-path`, e.g. `/some/sub-path` and
`/some/sub-path/abc` and `/some/sub-path/123/another/sub-path` etc. Thus, if we were to send a request to the above with
the url `/some/sub-path/abc`, the handler will be invoked and the value of `scope["path"]` will equal `/`. If we send a
request to `/some/sub-path/abc`, it will also be invoked, and `scope["path"]` will equal `/abc`.
