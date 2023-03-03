2.x Changelog
=============

2.0.0alpha1
-----------

New features
++++++++++++

Validation of controller route handler methods
    Starlite will now validate that no duplicate handlers (that is, they have the same
    path and same method) exist.

    Reference: https://github.com/starlite-api/starlite/pull/1144

HTMX support
    Basic support for HTMX requests and responses.

    Reference: https://github.com/starlite-api/starlite/pull/1086

Alternate constructor ``Starlite.from_config``
    :meth:`Starlite.from_config <starlite.app.Starlite.from_config>` was added to the
    :class:`Starlite <starlite.app.Starlite>` class which allows to construct an instance
    from an :class:`AppConfig <starlite.config.app.AppConfig>` instance.

    Reference: https://github.com/starlite-api/starlite/pull/1190

Web concurrency option for CLI ``run`` command
    A ``--wc`` / --web-concurrency` option was added to the ``starlite run`` command,
    enabling users to specify the amount of worker processes to use. A corresponding
    environment variable ``WEB_CONCURRENCY`` was added as well

    Reference: https://github.com/starlite-api/starlite/pull/1218

Validation of ``state`` parameter in handler functions
    Type annotations of the reserved ``state`` parameter in handler functions will
    now be validated such that annotations using an unsupported type will raise a
    :class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>`.

    Reference: https://github.com/starlite-api/starlite/pull/1264

Generic application state
    :class:`ASGIConnection <starlite.connection.base.ASGIConnection>` and its subclasses are now generic on ``State``
    which allow to to fully type hint a request as ``Request[UserType, AuthType, StateType]``.

    Reference: https://github.com/starlite-api/starlite/pull/1030

Dependency injection of classes
    Support using classes (not class instances, which were already supported) as dependency providers.
    With this, now every callable is supported as a dependency provider.

    Reference: https://github.com/starlite-api/starlite/pull/1143

Event bus
    A simple event bus system for Starlite, supporting synchronous and asynchronous listeners and emitters, providing a
    similar interface to handlers. It currently features a simple in-memory, process-local backend. For the future,
    backends that allow inter-process event dispatching are planned.

    Reference: https://github.com/starlite-api/starlite/pull/1105

Unified storage interfaces **[Breaking]**
    Storage backends for server-side sessions and :class:`Cache <starlite.cache.Cache>` have been unified and replaced
    by the :doc:`storage module </lib/usage/storage>`, which implements generic asynchronous key/values stores backed
    by memory, the file system or redis.

    .. important::
        This is a breaking change and you need to change your session / cache configuration accordingly

    Reference: https://github.com/starlite-api/starlite/pull/1184
