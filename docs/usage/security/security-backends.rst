Security Backends
=================

AbstractSecurityConfig
----------------------

:doc:`/reference/security/index` includes an :class:`AbstractSecurityConfig <.security.base.AbstractSecurityConfig>` class
that serves as a basis for all the security backends offered by Starlite, and is also meant to be used as a basis for
custom security backends created by users.

Session Auth Backend
--------------------

Starlite offers a builtin session auth backend that can be used out of the box with any of the
:ref:`session backends <usage/middleware/builtin-middleware:session middleware>` supported by the Starlite session
middleware.

.. literalinclude:: /examples/security/using_session_auth.py
    :caption: Using Session Auth
    :language: python


JWT Auth
--------

Starlite also includes several JWT security backends under the contrib package, checkout
the :doc:`jwt contrib documentation </usage/contrib/jwt>` for more details.
