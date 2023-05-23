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
| ``starlite.BackgroundTask``                        | :class:`.background_tasks.BackgroundTask`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTasks``                       | :class:`.background_tasks.BackgroundTasks`                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Configuration**                                                                                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AllowedHostsConfig``                    | :class:`.config.allowed_hosts.AllowedHostsConfig`                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CacheConfig``                           | :class:`.config.response_cache.ResponseCacheConfig`                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CompressionConfig``                     | :class:`.config.compression.CompressionConfig`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CORSConfig``                            | :class:`.config.cors.CORSConfig`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CSRFConfig``                            | :class:`.config.csrf.CSRFConfig`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIConfig``                         | :class:`.openapi.OpenAPIConfig`                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StaticFilesConfig``                     | :class:`.static_files.config.StaticFilesConfig`                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TemplateConfig``                        | :class:`.template.TemplateConfig`                                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BaseLoggingConfig``                     | :class:`.logging.config.BaseLoggingConfig`                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.LoggingConfig``                         | :class:`.logging.config.LoggingConfig`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StructLoggingConfig``                   | :class:`.logging.config.StructLoggingConfig`                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Provide**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.Provide``                | :class:`.di.Provide`                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Pagination**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncClassicPaginator``         | :class:`.pagination.AbstractAsyncClassicPaginator`                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncCursorPaginator``          | :class:`.pagination.AbstractAsyncCursorPaginator`                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncOffsetPaginator``          | :class:`.pagination.AbstractAsyncOffsetPaginator`                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncClassicPaginator``          | :class:`.pagination.AbstractSyncClassicPaginator`                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncCursorPaginator``           | :class:`.pagination.AbstractSyncCursorPaginator`                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncOffsetPaginator``           | :class:`.pagination.AbstractSyncOffsetPaginator`                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ClassicPagination``                     | :class:`.pagination.ClassicPagination`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CursorPagination``                      | :class:`.pagination.CursorPagination`                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OffsetPagination``                      | :class:`.pagination.OffsetPagination`                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Response containers**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.File``                                  | :class:`.response_containers.File`                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Redirect``                              | :class:`.response_containers.Redirect`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseContainer``                     | :class:`.response_containers.ResponseContainer`                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Stream``                                | :class:`.response_containers.Stream`                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Template``                              | :class:`.response_containers.Template`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Exceptions**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HTTPException``                         | :class:`.exceptions.HTTPException`                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImproperlyConfiguredException``         | :class:`.exceptions.ImproperlyConfiguredException`                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.InternalServerException``               | :class:`.exceptions.InternalServerException`                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MissingDependencyException``            | :class:`.exceptions.MissingDependencyException`                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NoRouteMatchFoundException``            | :class:`.exceptions.NoRouteMatchFoundException`                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotAuthorizedException``                | :class:`.exceptions.NotAuthorizedException`                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotFoundException``                     | :class:`.exceptions.NotFoundException`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.PermissionDeniedException``             | :class:`.exceptions.PermissionDeniedException`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ServiceUnavailableException``           | :class:`.exceptions.ServiceUnavailableException`                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StarliteException``                     | :class:`.exceptions.LitestarException`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TooManyRequestsException``              | :class:`.exceptions.TooManyRequestsException`                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ValidationException``                   | :class:`.exceptions.ValidationException`                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebSocketException``                    | :class:`.exceptions.WebSocketException`                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Testing**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TestClient``                            | :class:`.testing.TestClient`                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AsyncTestClient``                       | :class:`.testing.AsyncTestClient`                                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_test_client``                    | :class:`.testing.create_test_client`                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIController``                     | :class:`.openapi.controller.OpenAPIController`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseSpec``                          | :class:`.openapi.datastructures.ResponseSpec`                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Middleware**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAuthenticationMiddleware``      | :class:`.middleware.authentication.AbstractAuthenticationMiddleware`   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AuthenticationResult``                  | :class:`.middleware.authentication.AuthenticationResult`               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractMiddleware``                    | :class:`.middleware.AbstractMiddleware`                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DefineMiddleware``                      | :class:`.middleware.DefineMiddleware`                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MiddlewareProtocol``                    | :class:`.middleware.MiddlewareProtocol`                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Security**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | :class:`.security.AbstractSecurityConfig`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Handlers**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.asgi``                         | :mod:`.handlers`                                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.http``                         | :mod:`.handlers`                                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.handlers.websocket``                    | :class:`.handlers`                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+


Response headers
----------------

Response header can now be set using either a :class:`Sequence <typing.Sequence>` of
:class:`ResponseHeader <.datastructures.response_header.ResponseHeader>`, or by using a
plain :class:`Mapping[str, str] <typing.Mapping>`. The typing of
:class:`ResponseHeader <.datastructures.response_header.ResponseHeader>` was also
changed to be more strict and now only allows string values.



.. code-block:: python
    :caption: 1.51

    from starlite import ResponseHeader, get


    @get(response_headers={"my-header": ResponseHeader(value="header-value")})
    async def handler() -> str:
        ...


.. code-block:: python
    :caption: 2.x

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


.. code-block:: python

    @get("/", response_cookies=[Cookie(key="foo", value="bar")])
    async def handler() -> None:
        ...

is equivalent to

.. code-block:: python

    @get("/", response_cookies={"foo": "bar"})
    async def handler() -> None:
        ...


SQLAlchemy Plugin
-----------------

Support for SQLAlchemy 1 has been dropped and the new plugin will now support
SQLAlchemy 2 only.

TODO: Migration instructions

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
should be changed to include an additional ``scope`` parameter.


.. code-block:: python
    :caption: 1.51

    async def before_send(message: Message, state: State) -> None:
        ...


.. code-block:: python
    :caption: 2.x

    async def before_send(message: Message, state: State, scope: Scope) -> None:
        ...



.. seealso::
    :ref:`change:2.0.0alpha2-remove support for 2 argument form of`
    :ref:`before_send`


``initial_state`` application parameter
---------------------------------------

The ``initial_state`` argument to :class:`~litestar.app.Litestar` has been replaced
with a ``state`` keyword argument, accepting an optional
:class:`~litestar.datastructures.state.State` instance.



Existing code using this keyword argument will need to be changed from

.. code-block:: python
    :caption: 1.51


    app = Starlite(..., initial_state={"some": "key"})

to

.. code-block:: python
    :caption: 2.x

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

DTOs are now defined using the ``dto`` and ``return_dto`` arguments to
handlers/controllers/routers and the application.

A DTO is any type that conforms to the :class:`litestar.dto.interface.DTOInterface`
protocol.

Litestar provides a suite of factory types that implement the ``DTOInterface`` protocol
and can be used to define DTOs:

- :class:`litestar.dto.factory.stdlib.DataclassDTO`
- :class:`litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO`
- :class:`litestar.contrib.pydantic.PydanticDTO`
- :class:`litestar.contrib.msgspec.MsgspecDTO`
- ``litestar.contrib.piccolo.PiccoloDTO`` (TODO)
- ``litestar.contrib.tortoise.TortoiseDTO`` (TODO)

For example, to define a DTO from a dataclass:

.. code-block:: python

    from dataclasses import dataclass

    from litestar import get
    from litestar.dto.factory import DTOConfig
    from litestar.dto.factory.stdlib import DataclassDTO


    @dataclass
    class MyType:
        some_field: str
        another_field: int


    class MyDTO(DataclassDTO[MyType]):
        config = DTOConfig(exclude={"another_field"})


    @get(dto=MyDTO)
    async def handler() -> MyType:
        return MyType(some_field="some value", another_field=42)


.. seealso::
    :doc:`/usage/dto/index`




Application lifespan hooks
--------------------------

All application lifespan hooks have been merged into ``on_startup`` and ``on_shutdown``.
The following hooks have been removed:

- ``before_startup``
- ``after_startup``
- ``before_shutdown``
- ``after_shutdown``


``on_startup`` and ``on_shutdown`` now optionally receive the application instance as
their first parameter. If your ``on_startup`` and ``on_shutdown`` hooks made use of the
application state, they will now have to access it through the provided application
instance.

.. code-block:: python
    :caption: 1.51

    def on_startup(state: State) -> None:
        print(state.something)


.. code-block:: python
    :caption: 2.x

    def on_startup(app: Litestar) -> None:
        print(app.state.something)


Dependencies without ``Provide``
--------------------------------

Dependencies may now be declared without :class:`~litestar.di.Provide`, by passing the
callable directly. This can be advantageous in places where the configuration options
of :class:`~litestar.di.Provide` are not needed.

.. code-block:: python

    async def some_dependency() -> str:
        ...


    app = Litestar(dependencies={"some": Provide(some_dependency)})

is equivalent to


.. code-block:: python

    async def some_dependency() -> str:
        ...


    app = Litestar(dependencies={"some": some_dependency})


``sync_to_thread``
------------------

The ``sync_to_thread`` option can be use to run a synchronous callable provided to a
route handler or :class:`~litestar.di.Provide` inside a thread pool. Since synchronous
functions may block the main thread when not used with ``sync_to_thread=True``, a
warning will be raised in these cases. If the synchronous function should not be run in
a thread pool, passing ``sync_to_thread=False`` will also silence the warning.


.. tip::
    The warning can be disabled entirely by setting the environment variable
    ``LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD=0``



.. code-block:: python
    :caption: 1.51

    @get()
    def handler() -> None:
        ...



.. code-block:: python
    :caption: 2.x

    @get(sync_to_thread=False)
    def handler() -> None:
        ...

or

.. code-block:: python
    :caption: 2.x

    @get(sync_to_thread=True)
    def handler() -> None:
        ...


.. seealso::
    :doc:`/topics/sync-vs-async`
