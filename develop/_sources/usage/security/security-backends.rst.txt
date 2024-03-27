Security Backends
=================

AbstractSecurityConfig
----------------------

:doc:`/reference/security/index` includes an :class:`AbstractSecurityConfig <.security.base.AbstractSecurityConfig>` class
that serves as a basis for all the security backends offered by Litestar, and is also meant to be used as a basis for
custom security backends created by users.

Session Auth Backend
--------------------

Litestar offers a builtin session auth backend that can be used out of the box with any of the
:ref:`session backends <usage/middleware/builtin-middleware:session middleware>` supported by the Litestar session
middleware.

.. literalinclude:: /examples/security/using_session_auth.py
    :caption: Using Session Auth
    :language: python


JWT Auth
--------

Litestar includes several JWT security backends. Check out the
:doc:`jwt documentation </usage/security/jwt>` for more details.
