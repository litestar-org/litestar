JWT Security Backends
=====================

Litestar offers optional JWT based security backends. To use these make sure to install the
`pyjwt <https://pyjwt.readthedocs.io/en/stable/>`_ and `cryptography <https://github.com/pyca/cryptography>`_
packages, or simply install Litestar with the ``jwt``
`extra <https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras>`_:

.. code-block:: shell
    :caption: Install Litestar with JWT extra

    pip install 'litestar[jwt]'

:class:`JWT Auth <.security.jwt.JWTAuth>` Backend
-------------------------------------------------

This is the base JWT Auth backend. You can read about its particular API in the :class:`~.security.jwt.JWTAuth`.
It sends the JWT token using a header - and it expects requests to send the JWT token using the same header key.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_jwt_auth.py
        :language: python
        :caption: Using JWT Auth

:class:`JWT Cookie Auth <.security.jwt.JWTCookieAuth>` Backend
--------------------------------------------------------------

This backend inherits from the :class:`~.security.jwt.JWTAuth` backend, with the difference being
that instead of using a header for the JWT Token, it uses a cookie.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_jwt_cookie_auth.py
        :language: python
        :caption: Using JWT Cookie Auth

:class:`OAuth2 Bearer <.security.jwt.auth.OAuth2PasswordBearerAuth>` Password Flow
----------------------------------------------------------------------------------

The :class:`~.security.jwt.auth.OAuth2PasswordBearerAuth` backend inherits from the :class:`~.security.jwt.JWTCookieAuth`
backend. It works similarly to the :class:`~.security.jwt.JWTCookieAuth` backend, but is meant to be used for
OAuth 2.0 Bearer password flows.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_oauth2_password_bearer.py
       :language: python
       :caption: Using OAUTH2 Bearer Password


Using a custom token class
--------------------------

The token class used can be customized with arbitrary fields, by creating a subclass of
:class:`~.security.jwt.Token`, and specifying it on the backend:

.. literalinclude:: /examples/security/jwt/custom_token_cls.py
   :language: python
   :caption: Using a custom token


The token will be converted from JSON into the appropriate type, including basic type
conversions.

.. important::
    Complex type conversions, especially those including third libraries such as
    Pydantic or attrs, as well as any custom ``type_decoders`` are not available for
    converting the token. To support more complex conversions, the
    :meth:`~.security.jwt.Token.encode` and :meth:`~.security.jwt.Token.decode` methods
    must be overwritten in the subclass.


Verifying issuer and audience
-----------------------------

To verify the JWT ``iss`` (*issuer*) and ``aud`` (*audience*) claim, a list of accepted
issuers or audiences can bet set on the authentication backend. When a JWT is decoded,
the issuer or audience on the token is compared to the list of accepted issuers /
audiences. If the value in the token does not match any value in the respective list,
a :exc:`NotAuthorizedException` will be raised, returning a response with a
``401 Unauthorized`` status.


.. literalinclude:: /examples/security/jwt/verify_issuer_audience.py
   :language: python
   :caption: Verifying issuer and audience


Customizing token validation
----------------------------

Token decoding / validation can be further customized by overriding the
:meth:`~.security.jwt.Token.decode_payload` method. It will be called by
:meth:`~.security.jwt.Token.decode` with the encoded token string, and must return a
dictionary representing the decoded payload, which will then used by
:meth:`~.security.jwt.Token.decode` to construct an instance of the token class.


.. literalinclude:: /examples/security/jwt/custom_decode_payload.py
   :language: python
   :caption: Customizing payload decoding


Using token revocation
----------------------
Token revocation can be implemented by maintaining a list of revoked tokens and checking against this list during authentication.
When a token is revoked, it should be added to the list, and any subsequent requests with that token should be denied.

.. dropdown:: Click to see the code

    .. literalinclude:: /examples/security/jwt/using_token_revocation.py
        :language: python
        :caption: Implementing token revocation
