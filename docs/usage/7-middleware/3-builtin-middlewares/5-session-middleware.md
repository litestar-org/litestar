# Session Middleware

Starlite includes a [SessionMiddleware][starlite.middleware.session.SessionMiddleware], 
offering client- and server-side sessions which can help persisting per-client data
across requests.

!!! info
    The Starlite's `SesionMiddleware` is not based on the
    [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware), 
    although it is compatible with it, and it can act as a drop-in replacement.


## Setting up the middleware

To start using sessions in your application all you have to do is create an instance
of a [configuration][starlite.middleware.session.base.BaseBackendConfig] object, and 
add its middleware property to your application's middleware stack:

```py title="Hello World"
--8<-- "examples/middleware/session_middleware_simple.py"
```

This will create a client-side session, which stores data in encrypted cookies in the client (for example a browser)


## Session backends

`SessionMiddleware` not only supports storing data in cookies but offers a variety of 
server-side storage options as well, provided through [`SessionBackend`s][starlite.middleware.session.base.SessionBackend].

They fall in two categories:


Client-side
: Stores data in the client (typically a browser) in the form of cookies

Server-side
:   Stores session data on the server, and only a tiny piece string of information on the client 
    which is then used to later load the data back. This string is called a **Session ID** and 
    is typically stored in a cookie


### Which backend to pick

A cookie based sessions are usually a good starting point, as they require no extra
setup on the server, perform well and (when using encryption and signing) are secure.

One disadvantage however is, that an application has no direct control over the sessions.
It's not able to remotely invalidate them; This is only possible when the client whose session
you're looking to invalidate makes a request to your application. If you need full control
a server-side session is a better choice, since the backend where all the data is stored
lives alongside your application and can be accessed any given time. This also makes it 
possible to generate metrics for example about how many active (i.e. not-expired) sessions
there currently are.

!!! tip "In a hurry?"
    The cookie backend is probably the best choice for your application if you're just
    starting out and don't have specific needs


## Client-side sessions

Client side sessions are available through the [CookieBackend][starlite.middleware.session.cookie_backend.CookieBackend],
which offers strong AES-CGM encryption security best practices while support cookie splitting.

!!! important
    Although the `CookieBackend` offer compatible functionality with 
    [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware), 
    `CookieBackend` offers stronger security and is recommended. Using it requires
    the [cryptography](https://cryptography.io/en/latest/) library, which can be installed
    together with starlite as an extra using `pip install starlite[cryptography]`


For additional configuration options please see the [configuration references][starlite.middleware.session.cookie_backend.SessionCookieConfig].


## Server-side sessions
