JWT Security Backends
=====================

Litestar offers optional JWT based security backends. To use these make sure to install the
`python-jose <https://github.com/mpdavis/python-jose>`_ and `cryptography <https://github.com/pyca/cryptography>`_
packages, or simply install Litestar with the ``jwt``
`extra <https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras>`_:

.. code-block:: shell
    :caption: Install Litestar with JWT extra

    pip install litestar[jwt]

:class:`JWT Auth <.security.jwt.JWTAuth>` Backend
-------------------------------------------------

This is the base JWT Auth backend. You can read about its particular API in the :class:`~.security.jwt.JWTAuth`.
It sends the JWT token using a header - and it expects requests to send the JWT token using the same header key.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_jwt_auth.py
        :caption: Using JWT Auth

:class:`JWT Cookie Auth <.security.jwt.JWTCookieAuth>` Backend
--------------------------------------------------------------

This backend inherits from the :class:`~.security.jwt.JWTAuth` backend, with the difference being
that instead of using a header for the JWT Token, it uses a cookie.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_jwt_cookie_auth.py
        :caption: Using JWT Cookie Auth

:class:`OAuth2 Bearer <.security.jwt.auth.OAuth2PasswordBearerAuth>` Password Flow
----------------------------------------------------------------------------------

The :class:`~.security.jwt.auth.OAuth2PasswordBearerAuth` backend inherits from the :class:`~.security.jwt.JWTCookieAuth`
backend. It works similarly to the :class:`~.security.jwt.JWTCookieAuth` backend, but is meant to be used for
OAuth 2.0 Bearer password flows.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_oauth2_password_bearer.py
       :caption: Using OAUTH2 Bearer Password
