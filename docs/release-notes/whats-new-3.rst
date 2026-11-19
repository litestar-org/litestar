.. py:currentmodule:: litestar


What's changed in 3.0?
======================

This document is an overview of the changes between version **2.11.x** and **3.0**.
For a detailed list of all changes, including changes between versions leading up to the
3.0 release, consult the :doc:`/release-notes/changelog`.

.. note:: The **2.11** release line is unaffected by this change

Imports
-------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``2.x``                                            | ``3.x``                                                                |
+====================================================+========================================================================+
| ``litestar.contrib.attrs``                         | ``litestar.plugins.attrs``                                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.htmx``                          | ``litestar_htmx``                                                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.jinja``                         | ``litestar.plugins.jinja``                                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.jwt``                           | ``litestar.security.jwt``                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.mako``                          | ``litestar.plugins.mako``                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.minijinja``                     | ``litestar.plugins.minijinja``                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.minijnja``                      | ``litestar.plugins.minijinja``                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.opentelemetry``                 | ``litestar.plugins.opentelemetry``                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.piccolo``                       | ``litestar_piccolo``                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.prometheus``                    | ``litestar.plugins.prometheus``                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.pydantic``                      | ``litestar.plugins.pydantic``                                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.repository``                    | ``litestar.repository``                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.contrib.sqlalchemy``                    | ``advanced_alchemy.extensions.litestar``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.pagination.OffsetPagination``           | ``advanced_alchemy.service.OffsetPagination``                          |
+----------------------------------------------------+------------------------------------------------------------------------+


Removal of ``StaticFileConfig``
-------------------------------

The ``StaticFilesConfig`` has been removed, alongside these related parameters and
functions:

- ``Litestar.static_files_config``
- ``Litestar.url_for_static_asset``
- ``Request.url_for_static_asset``

:func:`create_static_files_router` is a drop-in replacement for ``StaticFilesConfig``,
and can simply be added to the ``route_handlers`` like any other regular handler.

Usage of ``url_for_static_assets`` should be replaced with a ``url_for("static", ...)``
call.


Implicit Optional Default Parameters
------------------------------------

In v2, if a handler was typed with an optional parameter it would be implicitly given a default value of ``None``. For
example, if the following handler is called with no query parameter, the value ``None`` would be passed in to the
handler for the ``param`` parameter:

.. code-block:: python

    @get("/")
    def my_handler(param: int | None) -> ...:
        ...

This legacy behavior originates from our history of using Pydantic v1 models to represent handler signatures. In v3, we
no longer make this implicit conversion. If you want to have a default value of ``None`` for an optional parameter, you
must explicitly set it:

.. code-block:: python

    @get("/")
    def my_handler(param: int | None = None) -> ...:
        ...


Path parameters must be marked
------------------------------

Only a parameter marked with :data:`~.params.FromPath` or :class:`~.params.PathParameter`
is read from the path. In v2, a parameter whose name matched a path segment was read from
the path even when it was marked as a query, header or cookie parameter. In v3 it is read
from the location it is marked with:

.. code-block:: python

    @get("/{item_id:int}")
    def my_handler(item_id: FromQuery[int]) -> ...:  # read from the query string
        ...

A parameter named like a path segment that declares no location, such as the deprecated
``item_id: int``, raises :exc:`~.exceptions.ImproperlyConfiguredException` when the
application is created. Declare it as ``item_id: FromPath[int]``.


OpenAPI Controller Replaced by Plugins
--------------------------------------

In version 3.0, the OpenAPI controller pattern, deprecated in v2.8, has been removed in
favor of a more flexible plugin system.

Elimination of ``OpenAPIController`` Subclassing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously, users configured elements such as the root path and styling by subclassing OpenAPIController and setting it
on the ``OpenAPIConfig.openapi_controller`` attribute. As of version 3.0, this pattern has been removed. Instead, users
are required to transition to using UI plugins for configuration.

Migration Steps:

1. Remove any implementations subclassing ``OpenAPIController``.
2. Use the :attr:`OpenAPIConfig.render_plugins` attribute to configure the OpenAPI UI made available to your users.
   If no plugin is supplied, we automatically add the :class:`ScalarRenderPlugin` for the default configuration.
3. Use the :attr:`OpenAPIConfig.openapi_router` attribute for additional configuration.

See the :doc:`/usage/openapi/ui_plugins` documentation for more information on how to configure OpenAPI plugins.

Changes to Endpoint Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``OpenAPIConfig.enabled_endpoints`` attribute is no longer available in version 3.0.0. This attribute previously
enabled a set of endpoints that would serve different OpenAPI UIs. In the new version, only the ``openapi.json``
endpoint is enabled by default, alongside the ``Scalar`` UI plugin as the default.

To adapt to this change, you should explicitly configure any additional endpoints you need by properly setting up the
necessary plugins within the :attr:`OpenAPIConfig.render_plugins` parameter.

Modification to ``root_schema_site`` Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``root_schema_site`` attribute, which enabled serving a particular UI at the OpenAPI root path, has been removed in
version 3.0. The new approach automatically assigns the first :class:`OpenAPIRenderPlugin` listed in the
:attr:`OpenAPIConfig.render_plugins` list to serve at the ``/schema`` endpoint, unless a plugin has been defined with
the root path (``/``), in which case that plugin will be used.

For those previously using the ``root_schema_site`` attribute, the migration involves ensuring that the UI intended to
be served at the ``/schema`` endpoint is the first plugin listed in the :attr:`OpenAPIConfig.render_plugins`.


Removal of the RapiDoc OpenAPI UI plugin
----------------------------------------

The ``RapidocRenderPlugin`` has been removed due to lack of upstream maintenance.

If you were using ``RapidocRenderPlugin``, migrate to one of the other bundled UI plugins
via :attr:`OpenAPIConfig.render_plugins`, e.g. :class:`ScalarRenderPlugin` (the default),
:class:`SwaggerRenderPlugin`, :class:`RedocRenderPlugin` or :class:`StoplightRenderPlugin`.


Deprecated ``app`` parameter for ``Response.to_asgi_response`` has been removed
-------------------------------------------------------------------------------

The parameter ``app`` for :meth:`~response.Response.to_asgi_response` has been removed.
If you need access to the app instance inside a custom ``to_asgi_response`` method,
replace the usages of ``app`` with ``request.app``.


Deprecated scope state utilities removed
----------------------------------------

Litestar has previously made available utilities for storing and retrieving data in the ASGI scope state. These
utilities have been removed in version 3.0.0. If you need to store data in the ASGI scope state, you should use do so
using a namespace that is unique to your application and unlikely to conflict with other applications.

The following utilities have been removed:

- ``get_litestar_scope_state``
- ``set_litestar_scope_state``
- ``delete_litestar_scope_state``


Deprecated utility function ``is_sync_or_async_generator`` removed
------------------------------------------------------------------

The utility function ``is_sync_or_async_generator`` has been removed as it is no longer used internally.

If you were relying on this utility, you can define it yourself as follows:

.. code-block:: python

    from inspect import isasyncgenfunction, isgeneratorfunction

    def is_sync_or_async_generator(obj: Any) -> bool:
        return isgeneratorfunction(obj) or isasyncgenfunction(obj)


Deprecated ``DTOField`` declaration via Pydantic's ``Field.extra`` removed
--------------------------------------------------------------------------

Declaring a :class:`~.dto.field.DTOField` through Pydantic's ``Field.extra``, that is
``Field(**dto_field("read-only"))``, is no longer supported. The mark was already being
ignored in 2.x and only produced a deprecation warning.

Remove the declaration: it leaves an internal key in the field's ``json_schema_extra``,
which can make OpenAPI schema generation fail.

Before:

.. code-block:: python

    import pydantic

    from litestar.dto import dto_field


    class User(pydantic.BaseModel):
        id: int = pydantic.Field(**dto_field("read-only"))

After:

.. code-block:: python

    from typing import Annotated

    import pydantic

    from litestar.dto import DTOField


    class User(pydantic.BaseModel):
        id: Annotated[int, DTOField(mark="read-only")]


Removal of the ``litestar.pagination`` module
---------------------------------------------

The ``litestar.pagination`` module has been removed, together with the internal OpenAPI
schema plugin that gave its containers a schema of their own:

- ``ClassicPagination``
- ``OffsetPagination``
- ``CursorPagination``
- ``AbstractSyncClassicPaginator``
- ``AbstractAsyncClassicPaginator``
- ``AbstractSyncOffsetPaginator``
- ``AbstractAsyncOffsetPaginator``
- ``AbstractSyncCursorPaginator``
- ``AbstractAsyncCursorPaginator``

``OffsetPagination`` has a direct replacement: Litestar re-exported Advanced Alchemy's
container whenever the package was installed, so for an application that already depended
on it the class is the same one and only the import changes, to
``from advanced_alchemy.service import OffsetPagination``. It is exported from
``advanced_alchemy.service``, not from ``advanced_alchemy.extensions.litestar``. An
application that did not depend on Advanced Alchemy has to add it, directly or through the
``litestar[sqlalchemy]`` extra, or declare the same four-field container itself --
``items``, ``limit``, ``offset`` and ``total`` -- which serialises identically. Note that
Advanced Alchemy declares ``items`` as a ``Sequence[T]``, where the removed fallback
declared it as a ``list[T]``.

The other two containers and the six paginator base classes have no replacement in
Litestar or in Advanced Alchemy. Declare the container you need as a generic dataclass of
your own, and implement the paginating logic in the handler, or in a dependency whose
parameter is marked with :data:`~litestar.di.NamedDependency`. OpenAPI schema generation
resolves a generic dataclass wrapping a collection the same way, and DTOs still apply to
the models it holds.

.. code-block:: python

    from dataclasses import dataclass
    from typing import Generic, TypeVar

    T = TypeVar("T")


    @dataclass
    class ClassicPagination(Generic[T]):
        items: list[T]
        page_size: int
        current_page: int
        total_pages: int

``CursorPagination`` was generic over the cursor type first and the item type second, so a
handler annotated it as ``CursorPagination[str, Person]``:

.. code-block:: python

    C = TypeVar("C", int, str, UUID)


    @dataclass
    class CursorPagination(Generic[C, T]):
        items: list[T]
        results_per_page: int
        cursor: Optional[C]

The OpenAPI document changes for every paginated handler, including those of applications
that never imported ``litestar.pagination``, since the removed plugin matched Advanced
Alchemy's ``OffsetPagination`` as well. The response schema is now a reusable component
referenced with ``$ref``, named after the container and its type argument, instead of a
schema inlined per handler, with a ``required`` entry for each field and without the
per-field descriptions the plugin wrote. Behaviour and the response body are unchanged,
but regenerate any client generated from the document.


Removal of semantic HTTP route handler classes
-----------------------------------------------

The semantic ``HTTPRouteHandler`` classes have been removed in favour of functional
decorators. ``route``, ``get``, ``post``, ``patch``, ``put``, ``head`` and ``delete``
are now all decorator functions returning :class:`~.handlers.HTTPRouteHandler`
instances.

As a result, customizing the decorators directly is not possible anymore. Instead, to
use a route handler decorator with a custom route handler class, the ``handler_class``
parameter to the decorator function can be used:

Before:

.. code-block:: python

    class my_get_handler(get):
        ... # custom handler

    @my_get_handler()
    async def handler() -> Any:
        ...

After:

.. code-block:: python

    class MyHTTPRouteHandler(HTTPRouteHandler):
        ... # custom handler


    @get(handler_class=MyHTTPRouteHandler)
    async def handler() -> Any:
        ...


Deprecated ``app`` parameter for ``Response.to_asgi_response`` has been removed
-------------------------------------------------------------------------------

The parameter ``app`` for :meth:`~response.Response.to_asgi_response` has been removed.
If you need access to the app instance inside a custom ``to_asgi_response`` method,
replace the usages of ``app`` with ``request.app``.


Removal of deprecated ``litestar.middleware.exceptions`` module and ``ExceptionHandlerMiddleware``
--------------------------------------------------------------------------------------------------

The deprecated ``litestar.middleware.exceptions`` module and the
``ExceptionHandlerMiddleware`` have been removed. Since ``ExceptionHandlerMiddleware``
has been applied automatically behind the scenes if necessary, no action is required.


Update MessagePack media type to ``application/vnd.msgpack``
------------------------------------------------------------

Change the default media type of ``MessagePack`` from ``application/x-msgpack`` to the
newly introduced official ``application/vnd.msgpack``.

https://www.iana.org/assignments/media-types/application/vnd.msgpack


Deprecated ``resolve_`` methods on route handlers
-------------------------------------------------

All ``resolve_`` methods on the route handlers
(e.g. ``HTTPRouteHandler.resolve_response_headers``) have been
deprecated and will be removed in ``4.0``. The attributes can now safely be accessed
directly (e.g. `HTTPRouteHandlers.response_headers`).


Moved routing related methods from ``Router`` to ``Litestar``
-------------------------------------------------------------

:class:`~litestar.router.Router` now only holds route handlers and configuration, while
the actual routing is done in :class:`~litestar.app.Litestar`. With this, several
methods and properties have been moved from ``Router`` to ``Litestar``:

- ``route_handler_method_map``
- ``get_route_handler_map``
- ``routes``


Removal of  ``CLIPluginProtocol``
---------------------------------

The :class:`~typing.Protocol` ``CLIPluginProtocol`` has been removed in favour
of the abstract ``CLIPluginProtocol``. The functionality and interface remain the same,
the only difference being that plugins that wish to provide this functionality are now
required to inherit from :class:`~.plugins.CLIPlugin`.


Removal of ``OpenAPISchemaPluginProtocol``
------------------------------------------

The :class:`~typing.Protocol` ``OpenAPISchemaPluginProtocol`` has been removed in favour
of the abstract :class:`~litestar.plugins.OpenAPISchemaPlugin`. The functionality and
interface remain the same, the only difference being that plugins that wish to provide
this functionality are now required to inherit from
:class:`~.plugins.OpenAPISchemaPlugin`.


Dropped support for starlette middleware protocol
-------------------------------------------------

The `starlette middleware protocol <https://starlette.dev/middleware/>`_ is no longer
supported.

Only the "factory" pattern will now be supported, i.e. a callable that receives an ASGI
callable as its only argument and returns another ASGI callable:

.. code-block:: python

    def middleware(app: ASGIApp) -> ASGIApp:
        ...


.. seealso::
    :doc:`/usage/middleware/index`


Built-in middleware migrated to ``ASGIMiddleware``
--------------------------------------------------

Litestar's built-in middleware are being moved from the legacy ``AbstractMiddleware`` and
``MiddlewareProtocol`` bases onto :class:`~litestar.middleware.ASGIMiddleware`.
``CORSMiddleware``, ``ResponseCacheMiddleware`` and ``CSRFMiddleware`` have made this
move. ``ResponseCacheMiddleware`` and ``CSRFMiddleware`` have also been moved into
``litestar.middleware._internal``, removing them from the public API; for CSRF this
includes the ``litestar.middleware.csrf`` module and its ``generate_csrf_token`` /
``generate_csrf_hash`` helpers.

These classes are constructed by Litestar itself from their configuration objects (for
CSRF, via a ``from_config`` classmethod on the middleware), so applications that only
configure them - for CORS, via
:class:`~litestar.config.cors.CORSConfig`, for response caching, via
:class:`~litestar.config.response_cache.ResponseCacheConfig` and the handler-level
``cache`` argument, and for CSRF, via :class:`~litestar.config.csrf.CSRFConfig` - are
unaffected, with one exception: :attr:`~litestar.config.csrf.CSRFConfig.exclude`
patterns are now matched against the **handler's path template**
(e.g. ``/user/{user_id:int}``) at startup, instead of the request path
(e.g. ``/user/1``) at runtime. Patterns targeting literal paths keep working; patterns
written to match expanded path parameters must be rewritten against the template.

Code that composed one of them directly into an ASGI stack must drop the ``app``
argument, pass the settings as keyword arguments rather than a configuration object, and
apply the instance to the next ASGI app:

.. code-block:: python

    # before
    middleware = CORSMiddleware(app=next_app, config=cors_config)

    # after
    middleware = CORSMiddleware(
        allow_origins=cors_config.allow_origins,
        allow_methods=cors_config.allow_methods,
        allow_headers=cors_config.allow_headers,
        allow_credentials=cors_config.allow_credentials,
        allow_origin_regex=cors_config.allow_origin_regex,
        expose_headers=cors_config.expose_headers,
        max_age=cors_config.max_age,
    )
    asgi_app = middleware(next_app)

The settings are copied on construction, so mutating ``CORSConfig`` after the application
has been created no longer affects the middleware.

Because ``ASGIMiddleware.__call__`` returns a closure rather than the middleware
instance, a middleware stack can no longer be introspected by walking the ``.app``
attribute of each layer.

Subclasses must also rename ``__call__`` to ``handle``, which receives the next ASGI app
as an additional ``next_app`` argument in place of ``self.app``.

.. seealso::
    :ref:`asgi-middleware-migration`


Removal of ``SerializationPluginProtocol``
------------------------------------------

The :class:`~typing.Protocol` ``SerializationPluginProtocol`` has been removed in favour
of the abstract :class:`~litestar.plugins.SerializationPlugin`. The functionality and
interface remain the same, the only difference being that plugins that wish to provide
this functionality are now required to inherit from
:class:`~.plugins.SerializationPlugin`.


Removal of ``body`` in streaming responses
-------------------------------------------

The unsupported ``body`` parameter of :class:`~.ASGIStreamingResponse`
and :class:`.ASGIFileResponse` has been removed.

This does not change any behaviour, as this parameter was previously ignored.


``polyfactory`` package removed from default dependencies
----------------------------------------------------------

The `polyfactory <https://polyfactory.litestar.dev/>`_ library has been moved from the
default dependencies to the ``litestar[polyfactory]`` package extra. It
is also included in ``litestar[full]``.


``pyyaml`` package removed from default dependencies
----------------------------------------------------

The `PyYAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_ library, used to render the
OpenAPI schema as YAML has been moved from the default dependencies to the
``litestar[yaml]`` package extra.


``litestar-htmx`` package removed from default dependencies
-----------------------------------------------------------

The `litestar-htmx <https://github.com/litestar-org/litestar-htmx/>`_ package powering
the :doc:`HTMX plugin </usage/htmx>` has been moved to the ``litestar[htmx]`` extra.


``click``, ``rich`` and ``rich-click`` packages removed from default dependencies
---------------------------------------------------------------------------------

The `click <https://click.palletsprojects.com/>`_, `rich <https://rich.readthedocs.io>`_
and `rich-click <https://github.com/ewels/rich-click>`_ libraries powering the
:doc:`CLI </usage/cli>` have been moved from the default dependencies to the
``litestar[cli]`` package extra. They are also included in ``litestar[standard]`` and
``litestar[full]``.

Installing ``litestar`` on its own therefore no longer provides the ``litestar`` command.
Invoking it without the extra raises a
:class:`MissingDependencyException <litestar.exceptions.MissingDependencyException>`
naming the extra to install:

.. code-block:: shell
    :caption: Install the CLI

    pip install 'litestar[cli]'


Test clients are based on ``httpx2``, installed via the ``testing`` extra
-------------------------------------------------------------------------

The :doc:`test clients </usage/testing>` were based on
`httpx <https://www.python-httpx.org/>`_, which was a default dependency. In 3.0 they
are based on `httpx2 <https://pydantic.dev/docs/httpx2/>`_, the fork of ``httpx``
maintained by Pydantic, and it is installed by the ``litestar[testing]`` extra rather
than by default.

Importing anything from :mod:`litestar.testing` without the extra installed raises a
:class:`MissingDependencyException <litestar.exceptions.MissingDependencyException>`
naming the extra to install:

.. code-block:: shell
    :caption: Install the testing extra

    pip install 'litestar[testing]'

``httpx2`` keeps the public API of ``httpx`` 0.28.1, but it is a distinct module, so
every reference in a test suite has to be renamed:

.. code-block:: python

    # before
    response: httpx.Response = client.get("/")
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()

    # after
    response: httpx2.Response = client.get("/")
    with pytest.raises(httpx2.HTTPStatusError):
        response.raise_for_status()

If you cannot rename a test suite yet, ``httpx2.alias_httpx()`` makes ``import httpx``
resolve to ``httpx2`` process-wide. It has to be called before anything imports
``httpx`` or ``httpcore``, and raises :exc:`RuntimeError` otherwise. Litestar never
calls it for you.

Beyond the rename, these are worth checking:

- :class:`~litestar.testing.TestClient` and
  :class:`~litestar.testing.AsyncTestClient` now subclass ``httpx2.Client`` and
  ``httpx2.AsyncClient``, and :func:`~litestar.testing.subprocess_sync_client` /
  :func:`~litestar.testing.subprocess_async_client` return ``httpx2`` clients.
- ``httpx2`` raises its own exceptions, which do not inherit from the ``httpx`` ones.
  An ``except httpx.HTTPError`` around a test client call stops matching, and does so
  silently if ``httpx`` is still installed for other reasons.
- The logger is named ``httpx2``. Logging configuration and ``caplog`` assertions
  that reference the ``httpx`` logger need updating.
- The clients inherit ``httpx2``'s ``sse()``, which works through the test transport,
  so ``httpx-sse`` is no longer needed. The inherited ``websocket()`` does not work
  against the test transport; use
  :meth:`websocket_connect <litestar.testing.TestClient.websocket_connect>` instead.
- :func:`~litestar.testing.subprocess_sync_client` and
  :func:`~litestar.testing.subprocess_async_client` send
  ``User-Agent: python-httpx2/<version>``. :class:`~litestar.testing.TestClient` and
  :class:`~litestar.testing.AsyncTestClient` keep sending ``testclient``.
- The extra pulls ``anyio>=4.10`` and ``idna>=3.18``, neither of which can be
  satisfied alongside a lower pin. TLS verification uses the operating system trust
  store via ``truststore`` rather than ``certifi``.


``rich-click>=1.9`` is now required by the CLI
-----------------------------------------------

The ``litestar[cli]`` extra now requires ``rich-click>=1.9``, which is needed for the
themed :doc:`CLI </usage/cli>` output. Previously ``rich-click`` was capped at ``<1.9``,
which silently disabled the theme, as the underlying option only exists from 1.9 onwards.

This only affects applications that additionally pin ``rich-click<1.9`` themselves.


Improved file system handling / fsspec integration
---------------------------------------------------

A more coherent :doc:`file system </usage/file_systems>` integration was added, with
improved support for `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_.
This new implementation is more stable, performant and consistent, and includes new
features such as random access to all supported file systems as well as streaming
(optionally with offsets, even if the underlying file system does not support it
natively).

.. seealso::
    :doc:`/usage/file_systems`


Removal of ``resolve_symlinks`` parameter to ``create_static_files_router``
---------------------------------------------------------------------------

``resolve_symlinks`` parameter of
:func:`~litestar.static_files.create_static_files_router` has been removed in favour of
the new
:paramref:`~litestar.static_files.create_static_files_router.allow_symlinks_outside_directory`
parameter.

.. attention::
    This has been intentionally made a breaking change because the new parameter has
    slightly different behaviour and defaults to ``False`` instead of ``True``.


Middleware configuration constraints
-------------------------------------

:class:`~litestar.middleware.ASGIMiddleware`\ s can now express constraints for how
they are applied in the middleware stack, which are then validated on application
startup.

.. seealso::

    :ref:`usage/middleware/creating-middleware:Configuration constraints`


``copy_scope`` defaults to ``True`` for ASGI handlers
-----------------------------------------------------

Every :func:`~.handlers.asgi` handler, mounted or not, now receives a copy of the ASGI
``scope``, so the wrapped application can no longer add, replace or remove top-level scope
keys seen by the outer application. In 2.x the default was ``None``, which passed the
original scope through, warned at registration and warned again when the wrapped
application mutated the scope. Both warnings are gone.

The copy is shallow, so nested values such as ``scope["state"]`` are still shared with the
outer scope.

Set ``copy_scope=False`` where the wrapped application is meant to communicate with the
outer application through the scope:

.. code-block:: python

    @asgi("/some/sub-path", is_mount=True, copy_scope=False)
    async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None: ...

You need the opt-out if the wrapped application writes a top-level scope key the outer
application reads, such as ``scope["user"]``, or calls
:meth:`~.connection.ASGIConnection.set_session` or
:meth:`~.connection.ASGIConnection.clear_session`, both of which rebind
``scope["session"]``. A mounted Starlette or FastAPI application also sets
``scope["endpoint"]`` and ``scope["route"]``, which outer Sentry or OpenTelemetry layers
read after the response to name the transaction. All of these now fail silently.

``copy_scope`` is set per handler; there is no router- or application-level equivalent, so
an application with several mounts opts out on each handler. A ``handler_class`` subclass
that pinned ``copy_scope`` by passing it to ``super().__init__()`` must now accept it as a
parameter and forward it, because :func:`~.handlers.asgi` always passes it.

.. seealso::

    :ref:`usage/routing/handlers:ASGI route handler considerations`


OpenAPI: usage metadata is no longer written to shared component schemas
-------------------------------------------------------------------------

Metadata given where a type is used, such as a ``description``, ``title``, ``schema_extra``, a default value or a
handler's ``content_encoding``, was also written to the type's schema in ``components/schemas``. Because that schema
is shared by every usage of the type, the metadata of whichever usage was generated first ended up on all of them.

The metadata is now only emitted next to the reference, and the component only describes the type:

.. code-block:: python

    @post("/")
    async def create_user(data: Annotated[User, Body(description="The user to create")]) -> User: ...

.. code-block:: json

    {
      "requestBody": {
        "content": {
          "application/json": {
            "schema": {
              "allOf": [{"$ref": "#/components/schemas/User"}],
              "description": "The user to create"
            }
          }
        }
      }
    }

To keep the metadata on a component, give the usage a component of its own with ``schema_component_key``:

.. code-block:: python

    data: Annotated[User, Body(description="The user to create", schema_component_key="NewUser")]


OpenAPI: component schemas of generic types are named after their type arguments
--------------------------------------------------------------------------------

The component schema of a parametrized generic type was named after the string representation of the type, which
included the module of every type argument: ``Page[Item]`` became ``Page_app.models.Item_``. It is now named
``Page_Item``. Clients generated from the schema will see the new names.

If two types end up with the same name, the names are told apart by the modules the types are defined in, as before.
To control the names, see :ref:`usage/openapi/schema_generation:Customizing component schema names`.


OpenAPI: an empty ``security`` lifts inherited requirements
-----------------------------------------------------------

``security=[]`` on a route handler, controller or router was treated as not set. It now lifts the security
requirements declared on the layers above it and in the :class:`~litestar.openapi.config.OpenAPIConfig`, and the
operations are documented with ``security: []``. Pass ``None``, or omit the parameter, to inherit the requirements.


OpenAPI: other changes to the generated document
------------------------------------------------

The following changes apply to documents of existing applications and may require regenerating clients:

- Responses of handlers returning :class:`~litestar.response.ServerSentEvent` are documented as ``text/event-stream``
  instead of ``application/json``.
- Responses of handlers returning :class:`~litestar.response.File` are documented under ``application/octet-stream``,
  or the handler's ``media_type``, instead of an empty media type.
- :class:`datetime.time` is documented with the ``time`` format instead of ``duration``.
- ``allowEmptyValue`` is only emitted for query parameters that set it, and response cookies are documented with
  ``examples`` instead of ``example``.
- Parameters declared on a router, controller or the application are documented after the parameters of the handler
  and its dependencies.
- A request body is only documented if the handler, or a dependency it uses, declares ``data``.
- Examples of component schemas are only generated if ``create_examples`` is enabled. A
  :class:`~litestar.openapi.datastructures.ResponseSpec` still generates examples for content that is not a
  component.
- Different classes with the same name and module whose schemas differ, e.g. classes created by a factory function,
  are documented as separate components, ``Thing`` and ``Thing_2``, numbered in registration order, instead of
  sharing the component of the class registered first.
- The ``pattern`` of Pydantic model fields declared with ``Field(pattern=...)``, or with ``constr`` or
  ``StringConstraints`` nested in another type, is documented.
- :class:`~decimal.Decimal` is documented as a number or a decimal string (``oneOf``) instead of ``string``, and a
  constrained ``bool`` as ``boolean`` instead of ``integer``. Bounds of ``date`` and ``datetime`` values move from
  ``minimum`` or ``maximum`` timestamps into the field description, and numeric bounds are no longer emitted on
  string schemas.
- Mappings with a length constraint are documented as ``object`` with ``minProperties`` / ``maxProperties`` instead of
  ``array``, constrained fixed-length tuples keep ``prefixItems``, and length constraints of variable-length
  sequences are emitted as ``minItems`` / ``maxItems``. A constrained multipart collection of
  :class:`~litestar.datastructures.UploadFile` is documented as an ``object`` whose ``files`` property carries the
  length constraint, like an unconstrained one plus the bound.
- Fixed-length tuples such as ``tuple[int, str]`` are documented with ``minItems`` and ``maxItems`` equal to their
  number of elements, and ``tuple[()]`` as an empty array instead of an empty schema.
- Constraints declared with a Pydantic ``Field`` inside a PEP 695 ``type`` alias are documented on Pydantic model
  fields annotated with the alias, e.g. ``minimum`` for ``type Limit = Annotated[int, Field(ge=0)]``.
- Responses of handlers returning ``Response[None]`` are documented without ``content`` if they cannot carry a body:
  status codes ``204``, ``304`` and below ``200``, and ``HEAD`` operations.
- Examples declared in the ``json_schema_extra`` of a Pydantic field are documented in every schema generated from
  the field, including those of subclasses and of parametrized generic models, instead of only the first one.
- Component schemas of Pydantic models with ``extra="forbid"`` and no field alias, of msgspec structs with
  ``forbid_unknown_fields=True`` and of DTOs that forbid unknown fields set ``additionalProperties`` to ``false``.
- :class:`ipaddress.IPv4Network`, :class:`ipaddress.IPv4Interface`, :class:`ipaddress.IPv6Network` and
  :class:`ipaddress.IPv6Interface` are documented with the ``ipv4-cidr`` and ``ipv6-cidr`` formats instead of
  ``ipv4`` and ``ipv6``. Pydantic's ``IPvAnyInterface`` and ``IPvAnyNetwork`` are documented as strings without a
  format.
- Path parameters are documented before all other parameters of an operation, in the order in which they appear in
  the path. Query, header and cookie parameters keep their relative order.
- Unions whose members may accept the same value, such as ``UUID | str``, ``int | float`` or a union of two models,
  are documented with ``anyOf`` instead of ``oneOf``. Unions of disjoint members keep ``oneOf``.
- Two route handlers for the same HTTP method on paths that differ only in the names of their path parameters, such
  as ``/items/{item_id}`` and ``/items/{name}``, raise an :exc:`~litestar.exceptions.ImproperlyConfiguredException`
  when the application starts with OpenAPI enabled, instead of documenting two paths, since only one of the handlers
  can be reached. Handlers for different methods on such paths are documented under one path, the
  alphabetically first, with the path parameters named after it.
