# Security Backends

## AbstractSecurityConfig

The package `starlite.security` includes an [`AbstractSecurityConfig`][starlite.security.AbstractSecurityConfig] class
that serves as a basis for all the security backends offered by Starlite, and is also meant to be used as a basis for
custom security backends created by users. You can read more about this class in
the [API References](../../reference/security/0-base.md).

## Session Auth Backend

Starlite offers a builtin session auth backend that can be used out of the box with any of the
[session backends](../7-middleware/builtin-middlewares#session-middleware) supported by the Starlite session
middleware.

```py title="Using Session Auth"
--8<-- "examples/security/using_session_auth.py"
```

## JWT Auth

Starlite also includes several JWT security backends under the contrib package, checkout
the [jwt contrib documentation](../18-contrib/1-jwt.md) for more details.
