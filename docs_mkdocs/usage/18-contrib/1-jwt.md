# JWT Security Backends

Starlite offers optional JWT based security backends. To use these make sure to install the `python-jose`
and `cryptography` packages, or simply install Starlite with the jwt extra: `pip install starlite[jwt]`.

## JWT Auth Backend

This is the base JWT Auth backend. You can read about its particular API in
the [API Reference][starlite.contrib.jwt.JWTAuth]. It sends the JWT token using a header - and it expects requests to
send the JWT token using the same header key.

```py title="Using JWT Auth"
--8<-- "examples/contrib/jwt/using_jwt_auth.py"
```

## JWT Cookie Auth Backend

This backend inherits from the [`JWTAuth`][starlite.contrib.jwt.JWTAuth] backend, with the difference being that instead
of using a header for the JWT Token, it uses a cookie. You can read more about this backend in
the [API Reference][starlite.contrib.jwt.JWTCookieAuth].

```py title="Using JWT Cookie Auth"
--8<-- "examples/contrib/jwt/using_jwt_cookie_auth.py"
```

## OAuth2 Bearer Password Flow

This backend inherits from the [`JWTCookieAuth`][starlite.contrib.jwt.JWTCookieAuth] backend. It works similarly to
the `JWTCookieAuth` backend, but is meant to be used for OAUTH2 Bearer password flows.

```py title="Using OAUTH2 Bearer Password"
--8<-- "examples/contrib/jwt/using_oauth2_password_bearer.py"
```
