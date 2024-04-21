AbstractAuthenticationMiddleware
================================

Litestar exports :class:`AbstractAuthenticationMiddleware <.middleware.authentication.AbstractAuthenticationMiddleware>`,
which is an Abstract Base Class (ABC) that implements the :class:`MiddlewareProtocol <.middleware.base.MiddlewareProtocol>`.
To add authentication to your app using this class as a basis, subclass it and implement the abstract method
:meth:`authenticate_request <.middleware.authentication.AbstractAuthenticationMiddleware.authenticate_request>`:

.. literalinclude:: /examples/security/middleware/auth_middleware_1.py
    :language: python


As you can see, ``authenticate_request`` is an async function that receives a connection instance and is supposed to return
an :class:`AuthenticationResult <.middleware.authentication.AuthenticationResult>` instance, which is a pydantic model
that has two attributes:

1. ``user``: a non-optional value representing a user. It's typed as ``Any`` so it receives any value, including ``None``.
2. ``auth``: an optional value representing the authentication scheme. Defaults to ``None``.

These values are then set as part of the "scope" dictionary, and they are made available as
:attr:`Request.user <.connection.ASGIConnection.user>`
and :attr:`Request.auth <.connection.ASGIConnection.auth>` respectively, for HTTP route handlers, and
:attr:`WebSocket.user <.connection.ASGIConnection.user>` and
:attr:`WebSocket.auth <.connection.ASGIConnection.auth>` for websocket route handlers.

Example: Implementing a JWTAuthenticationMiddleware
---------------------------------------------------

Since the above is quite hard to grasp in the abstract, lets see an example.

We start off by creating a user model. It can be implemented using pydantic, and ODM, ORM, etc. For the sake of the
example here lets say it's a SQLAlchemy model:

.. literalinclude:: /examples/security/middleware/auth_middleware_model.py
    :caption: my_app/db/models.py
    :language: python


We will also need some utility methods to encode and decode tokens. To this end we will use
the `python-jose <https://github.com/mpdavis/python-jose>`_ library. We will also create a pydantic model representing a
JWT Token:

.. literalinclude:: /examples/security/middleware/auth_middleware_jwt.py
    :caption: my_app/security/jwt.py
    :language: python


We can now create our authentication middleware:

.. literalinclude:: /examples/security/middleware/auth_middleware_creation.py
    :caption: my_app/security/authentication_middleware_cr.py
    :language: python


Finally, we need to pass our middleware to the Litestar constructor:

.. literalinclude:: /examples/security/middleware/auth_middleware_to_app.py
    :caption: my_app/main.py
    :language: python


That's it. The ``JWTAuthenticationMiddleware`` will now run for every request, and we would be able to access these in a
http route handler in the following way:

.. literalinclude:: /examples/security/middleware/auth_middleware_route.py
    :language: python


Or for a websocket route:

.. literalinclude:: /examples/security/middleware/auth_middleware_websocket.py
    :language: python


And if you'd like to exclude individual routes outside those configured:

.. literalinclude:: /examples/security/middleware/auth_middleware_exclude_route.py
    :language: python


And of course use the same kind of mechanism for dependencies:

.. literalinclude:: /examples/security/middleware/auth_middleware_dependencies.py
    :language: python
