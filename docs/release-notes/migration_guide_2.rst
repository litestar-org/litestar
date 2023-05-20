Litestar 2.0 migration guide
============================

.. py:currentmodule:: litestar


Changed module paths
---------------------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``1.51``                                           | ``2.x``                                                                |
+====================================================+========================================================================+
| **Datastructures**                                                                                                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.UploadFile``             | ``litestar.upload_file.UploadFile``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTask``                        | ``litestar.background_tasks.BackgroundTask``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTasks``                       | ``litestar.background_tasks.BackgroundTasks``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Configuration**                                                                                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AllowedHostsConfig``                    | ``litestar.config.allowed_hosts.AllowedHostsConfig``                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BaseLoggingConfig``                     | ``litestar.logging.BaseLoggingConfig``                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CacheConfig``                           | ``litestar.config.cache.CacheConfig``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CompressionConfig``                     | ``litestar.config.compression.CompressionConfig``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CORSConfig``                            | ``litestar.config.cors.CORSConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CSRFConfig``                            | ``litestar.config.csrf.CSRFConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.LoggingConfig``                         | ``litestar.logging.LoggingConfig``                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StructLoggingConfig``                   | ``litestar.logging.StructLoggingConfig``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIConfig``                         | ``litestar.openapi.OpenAPIConfig``                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StaticFilesConfig``                     | ``litestar.static_files.config.StaticFilesConfig``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TemplateConfig``                        | ``litestar.template.TemplateConfig``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.config.cache.CacheConfig``              | `starlite.config.response_cache.ResponseCacheConfig``                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Provide**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.Provide``                | ``litestar.di.Provide``                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Pagination**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncClassicPaginator``         | ``litestar.utils.pagination.AbstractAsyncClassicPaginator``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncCursorPaginator``          | ``litestar.utils.pagination.AbstractAsyncCursorPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncOffsetPaginator``          | ``litestar.utils.pagination.AbstractAsyncOffsetPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncClassicPaginator``          | ``litestar.utils.pagination.AbstractSyncClassicPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncCursorPaginator``           | ``litestar.utils.pagination.AbstractSyncCursorPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncOffsetPaginator``           | ``litestar.utils.pagination.AbstractSyncOffsetPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ClassicPagination``                     | ``litestar.utils.pagination.ClassicPagination``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CursorPagination``                      | ``litestar.utils.pagination.CursorPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OffsetPagination``                      | ``litestar.utils.pagination.OffsetPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Response containers**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.File``                                  | ``litestar.response_containers.File``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Redirect``                              | ``litestar.response_containers.Redirect``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseContainer``                     | ``litestar.response_containers.ResponseContainer``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Stream``                                | ``litestar.response_containers.Stream``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Template``                              | ``litestar.response_containers.Template``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Exceptions**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HTTPException``                         | ``litestar.exceptions.HTTPException``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImproperlyConfiguredException``         | ``litestar.exceptions.ImproperlyConfiguredException``                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.InternalServerException``               | ``litestar.exceptions.InternalServerException``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MissingDependencyException``            | ``litestar.exceptions.MissingDependencyException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NoRouteMatchFoundException``            | ``litestar.exceptions.NoRouteMatchFoundException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotAuthorizedException``                | ``litestar.exceptions.NotAuthorizedException``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotFoundException``                     | ``litestar.exceptions.NotFoundException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.PermissionDeniedException``             | ``litestar.exceptions.PermissionDeniedException``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ServiceUnavailableException``           | ``litestar.exceptions.ServiceUnavailableException``                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StarliteException``                     | ``litestar.exceptions.StarliteException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TooManyRequestsException``              | ``litestar.exceptions.TooManyRequestsException``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ValidationException``                   | ``litestar.exceptions.ValidationException``                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebSocketException``                    | ``litestar.exceptions.WebSocketException``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Testing**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TestClient``                            | ``litestar.testing.TestClient``                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AsyncTestClient``                       | ``litestar.testing.AsyncTestClient``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_test_client``                    | ``litestar.testing.create_test_client``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **DTO**                                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DTOFactory``                            | ``litestar.dto.DTOFactory``                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIController``                     | ``litestar.openapi.controller.OpenAPIController``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseSpec``                          | ``litestar.openapi.datastructures.ResponseSpec``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Middleware**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAuthenticationMiddleware``      | ``litestar.middleware.authentication.AbstractAuthenticationMiddleware``|
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AuthenticationResult``                  | ``litestar.middleware.authentication.AuthenticationResult``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractMiddleware``                    | ``litestar.middleware.AbstractMiddleware``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DefineMiddleware``                      | ``litestar.middleware.DefineMiddleware``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MiddlewareProtocol``                    | ``litestar.middleware.MiddlewareProtocol``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Security**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | ``litestar.security.AbstractSecurityConfig``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Handlers**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | ``litestar.security.AbstractSecurityConfig``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.asgi``                         | ``litestar.handlers.asgi_handlers``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.http``                         | ``litestar.handlers.http_handlers``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.websocket``                    | ``litestar.handlers.websocket_handlers``                               |
+----------------------------------------------------+------------------------------------------------------------------------+


Response headers
----------------

Response header can now be set using either a :class:`Sequence <typing.Sequence>` of
:class:`ResponseHeader <.datastructures.response_header.ResponseHeader>`, or by using a
plain :class:`Mapping[str, str] <typing.Mapping>`. The typing of
:class:`ResponseHeader <.datastructures.response_header.ResponseHeader>` was also
changed to be more strict and now only allows string values.


.. tab-set::

    .. tab-item:: 1.51

        .. code-block:: python

            from starlite import ResponseHeader, get


            @get(response_headers={"my-header": ResponseHeader(value="header-value")})
            async def handler() -> str:
                ...

    .. tab-item:: 2.x

        .. code-block:: python

            from litestar import ResponseHeader, get


            @get(response_headers=[ResponseHeader(name="my-header", value="header-value")])
            async def handler() -> str:
                ...


            # or


            @get(response_headers={"my-header": "header-value"})
            async def handler() -> str:
                ...


Response cookies
----------------

Response cookies might now also be set using a
:class:`Mapping[str, str] <typing.Mapping>`, analogous to `Response headers`_.


SQLAlchemy Plugin
-----------------

Support for SQLAlchemy 1 has been dropped and the new plugin will now support
SQLAlchemy 2 only.

.. seealso::
    :doc:`/usage/contrib/sqlalchemy`
    :doc:`/reference/contrib/sqlalchemy/index`


Removal of Pydantic models
--------------------------

Several Pydantic models used for configuration have been replaced with dataclasses or
plain classes. If you relied on implicit data conversion from these models or subclassed
them, you might need to adjust your code accordingly.


.. seealso::

    :ref:`change:2.0.0alpha1-replace pydantic models with dataclasses`


Plugin protocols
----------------

The plugin protocol has been split into three distinct protocols, covering different use
cases:

:class:`litestar.plugins.InitPluginProtocol`
    Hook into an application's initialization process

:class:`litestar.plugins.SerializationPluginProtocol`
    Extend the serialization and deserialization capabilities of an application

:class:`litestar.plugins.OpenAPISchemaPluginProtocol`
    Extend OpenAPI schema generation


Plugins that made use of all features of the previous API should simply inherit from
all three base classes.



Remove 2 argument ``before_send``
---------------------------------

The 2 argument for of ``before_send`` hook handlers has been removed. Existing handlers
should be changed to include an additional ``scope`` parameter

.. seealso::
    :ref:`change:2.0.0alpha2-remove support for 2 argument form of`
    :ref:`before_send`


``initial_state`` application parameter
---------------------------------------

The ``initial_state`` argument to :class:`~litestar.app.Litestar` has been replaced
with a ``state`` keyword argument, accepting an optional
:class:`~litestar.datastructures.state.State` instance.

.. seealso::
    :ref:`change:2.0.0alpha2-replace`


Existing code using this keyword argument will need to be changed from

.. code-block:: python

    from starlite import Starlite

    app = Starlite(..., initial_state={"some": "key"})

to

.. code-block:: python

        from litestar import Litestar
        from litestar.datastructures.state import State

        app = Litestar(..., state=State({"some": "key"}))



Usage of the ``stores`` for caching and other integrations
-----------------------------------------------------------

The newly introduced :doc:`stores </usage/stores>` have superseded the removed
``starlite.cache`` module in various places.

The following now make use of stores:

- :class:`~litestar.middleware.rate_limit.RateLimitMiddleware`
- :class:`~litestar.config.response_cache.ResponseCacheConfig`
- :class:`~litestar.middleware.session.server_side.ServerSideSessionConfig`

The following attributes have been renamed to reduce ambiguity:

- ``Starlite.cache_config`` > ``Litestar.response_cache_config``
- ``AppConfig.cache_config`` > :attr:`~litestar.config.app.AppConfig.response_cache_config`

In addition, the ``ASGIConnection.cache`` property has been removed. It can be replaced
by accessing the store directly as described in :doc:`stores </usage/stores>`


DTOs
----

TBD



SQLAlchemy plugin
-----------------

TBD



Application lifespan hooks
--------------------------

All application lifespan hooks have been merged into ``on_startup`` and ``on_shutdown``.
The following hooks have been removed:

- ``before_startup``
- ``after_startup``
- ``before_shutdown``
- ``after_shutdown``


``on_startup`` and ``on_shutdown`` now optionally receive the application instance as
their first parameter.
