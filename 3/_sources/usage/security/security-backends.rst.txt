=================
Security Backends
=================

:class:`~.security.base.AbstractSecurityConfig`
-----------------------------------------------

:doc:`litestar.security </reference/security/index>` includes an :class:`~.security.base.AbstractSecurityConfig`
class that serves as a basis for all the security backends offered by Litestar, and is also meant to be used as a
basis for custom security backends created by users which you can read more about here:
:doc:`/usage/security/abstract-authentication-middleware`

Session Auth Backend
--------------------

Litestar offers a builtin session auth backend that can be used out of the box with any of the
:ref:`session backends <usage/middleware/builtin-middleware:session middleware>` supported by the Litestar session
middleware.

.. dropdown:: Click to see an example of using the session auth backend

    .. literalinclude:: /examples/security/using_session_auth.py
        :language: python
        :caption: Using Session Auth

JWT Auth
--------

Litestar includes several JWT security backends. Check out the
:doc:`JWT documentation </usage/security/jwt>` for more details.
