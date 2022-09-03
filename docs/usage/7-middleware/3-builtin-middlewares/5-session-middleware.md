# Session Middleware

Starlite includes its own implementation of [SessionMiddleware][starlite.middleware.session.SessionMiddleware], which
offers strong AES-CGM encryption security best practices while support cookie splitting.

!!! important
    The Starlite `SessionMiddleware` is not based on the
    [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware), although it is compatible
    with it, and it can act as a drop-in replacement. The Starlite middleware offers stronger security and is
    recommended. It does require though the [cryptography](https://cryptography.io/en/latest/) library, so make sure to
    install it.

To use the `SessionMiddleware` simply create an instance of
[SessionCookieConfig][starlite.middleware.session.SessionCookieConfig] and pass the created middleware to any layer of
the application:

```py title="Hello World"
--8<-- "examples/middleware/session_middleware.py"
```

For additional configuration options please see the [configuration references][starlite.middleware.session.SessionCookieConfig].
