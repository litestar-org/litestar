# Authentication

Starlite is agnostic to any authentication mechanism(s) used - you can use JWT, session cookies, OIDC or any other
mechanism to authenticate users.

Saying that, Starlite does offer an [AbstractAuthenticationMiddleware](1-abstract-authentication-middleware.md) class
that is meant to make building authentication simpler.

Additionally, there are [official authentication libraries](2-official-authentication-libraries.md).
