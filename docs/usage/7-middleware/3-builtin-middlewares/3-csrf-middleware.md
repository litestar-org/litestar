# CSRF

CSRF ([Cross-site request forgery](https://en.wikipedia.org/wiki/Cross-site_request_forgery)) is a type of attack
where unauthorized commands are submitted from a user that the web application trusts. This attack often uses
social engineering that tricks the victim into clicking a URL that contains a maliciously crafted, unauthorized
request for a particular Web application. The user’s browser then sends this maliciously crafted request to the
targeted Web application. If the user is in an active session with the Web application, the application treats
this new request as an authorized request submitted by the user. Thus, the attacker can force the user to perform
an action the user didn't intend, for example:

```text
POST /send-money HTTP/1.1
Host: target.web.app
Content-Type: application/x-www-form-urlencoded

amount=1000usd&to=attacker@evil.com
```

This middleware prevents CSRF attacks by doing the following:

1. On the first "safe" request (e.g `GET`) - set a cookie with a special token created by the server
2. On each subsequent "unsafe" request (e.g `POST`) - make sure the request contains either a form field or
   an additional header that has this token

To enable CSRF protection in a Starlite application simply pass an instance of
[`CSRFConfig`][starlite.config.CSRFConfig] to the [Starlite constructor][starlite.app.Starlite]:

```python
from starlite import Starlite, CSRFConfig

csrf_config = CSRFConfig(secret="my-secret")

app = Starlite(route_handlers=[...], csrf_config=csrf_config)
```

Some routes can be marked as being exempt from the protection offered by this middleware via
[handler opts](../../2-route-handlers/5-handler-opts.md)

```python
from starlite import post


@post("/post", exclude_from_csrf=True)
def handler() -> None:
    ...
```

If you need to exempt many routes at once you might want to consider using [`exclude`][starlite.config.CSRFConfig.exclude]
kwarg which accepts list of path patterns to skip in the middleware.

See the [API Reference][starlite.config.CSRFConfig] for full details on the `CSRFConfig` class and the kwargs it accepts.
