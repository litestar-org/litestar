==================================
Implementing Custom Authentication
==================================

Litestar exports :class:`~.middleware.authentication.AbstractAuthenticationMiddleware`, which is an
:term:`abstract base class` (ABC) that implements the :class:`~.middleware.base.MiddlewareProtocol`.
To add authentication to your app using this class as a basis, subclass it and implement the abstract method
:meth:`~.middleware.authentication.AbstractAuthenticationMiddleware.authenticate_request`:

.. code-block:: python
    :caption: Adding authentication to your app by subclassing
      :class:`~.middleware.authentication.AbstractAuthenticationMiddleware`

    from litestar.middleware import (
       AbstractAuthenticationMiddleware,
       AuthenticationResult,
    )
    from litestar.connection import ASGIConnection


    class MyAuthenticationMiddleware(AbstractAuthenticationMiddleware):
       async def authenticate_request(
           self, connection: ASGIConnection
       ) -> AuthenticationResult:
           # do something here.
           ...

As you can see, ``authenticate_request`` is an async function that receives a connection instance and is supposed to return
an :class:`~.middleware.authentication.AuthenticationResult` instance, which is a
:doc:`dataclass <python:library/dataclasses>` that has two attributes:

1. ``user``: a non-optional value representing a user. It is typed as ``Any`` so it receives any value,
   including ``None``.
2. ``auth``: an optional value representing the authentication scheme. Defaults to ``None``.

These values are then set as part of the ``scope`` dictionary, and they are made available as
:attr:`Request.user <.connection.ASGIConnection.user>`
and :attr:`Request.auth <.connection.ASGIConnection.auth>` respectively, for HTTP route handlers, and
:attr:`WebSocket.user <.connection.ASGIConnection.user>` and
:attr:`WebSocket.auth <.connection.ASGIConnection.auth>` for websocket route handlers.

Creating a Custom Authentication Middleware
-----------------------------------------------

Since the above is quite hard to grasp in the abstract, let us see an example.

We start off by creating a user model. It can be implemented using msgspec, Pydantic, an ODM, ORM, etc.
For the sake of this example here let us say it is a dataclass:

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 19-26
    :language: python
    :caption: user and token models


We can now create our authentication middleware:

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines:  29-43
    :language: python
    :caption: authentication_middleware.py


Finally, we need to pass our middleware to the Litestar constructor:


.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 80-88
    :language: python
    :caption: main.py


That is it. ``CustomAuthenticationMiddleware`` will now run for every request, and we would be able to access these in a
http route handler in the following way:

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 46-51
    :language: python
    :caption: Accessing the user and auth in a http route handler with ``CustomAuthenticationMiddleware``

Or for a websocket route:

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 54-59
    :language: python
    :caption: Accessing the user and auth in a websocket route handler with ``CustomAuthenticationMiddleware``


And if you would like to exclude individual routes outside those configured:


.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 62-70
    :language: python
    :caption: Excluding individual routes from ``CustomAuthenticationMiddleware``

And of course use the same kind of mechanism for dependencies:

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 73-77
    :language: python
    :caption: Using ``CustomAuthenticationMiddleware`` in a dependency
