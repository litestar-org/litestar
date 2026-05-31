.. py:currentmodule:: litestar

3.0 有哪些变化？
======================

本文档概述了 **2.11.x** 版本与 **3.0** 之间的变化。
如需详细了解所有变更，包括 3.0 发布前的各版本变更，请查阅 :doc:`/release-notes/changelog`。

.. note:: **2.11** 版本线不受此更改影响

导入路径变化
-------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``2.x``                                            | ``3.x``                                                                |
+====================================================+========================================================================+
| **SECTION**                                        | **SECTION**                                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| 请在此处填写 v2 的变更内容                         | 请在此处填写 v3 的变更内容                                             |
+----------------------------------------------------+------------------------------------------------------------------------+

移除 ``StaticFileConfig``
-------------------------------

`StaticFilesConfig` 已被移除，相关参数和函数如下：

- `Litestar.static_files_config`
- `Litestar.url_for_static_asset`
- `Request.url_for_static_asset`

`create_static_files_router` 可直接替代 `StaticFilesConfig`，只需像普通处理器一样添加到 `route_handlers`。

`url_for_static_assets` 的用法应替换为 `url_for("static", ...)`。

隐式可选默认参数
------------------------------------

在 v2 中，如果处理器参数类型为可选，则会隐式赋值为 `None`。例如，以下处理器如果未传递查询参数，则 `param` 参数会被赋值为 `None`：

.. code-block:: python

    @get("/")
    def my_handler(param: int | None) -> ...:
        ...

这种行为源自早期使用 Pydantic v1 模型表示处理器签名。在 v3 中不再进行隐式转换。如果需要默认值为 `None`，需显式设置：

.. code-block:: python

    @get("/")
    def my_handler(param: int | None = None) -> ...:
        ...

OpenAPI 控制器被插件替代
----------------------

3.0 版本中，OpenAPI 控制器模式（v2.8 弃用）已被更灵活的插件系统替代。

移除 ``OpenAPIController`` 子类化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

此前，用户通过继承 OpenAPIController 并设置到 `OpenAPIConfig.openapi_controller` 属性来配置根路径和样式。3.0 版本已移除该模式，需改用 UI 插件进行配置。

迁移步骤：

1. 移除所有继承 ``OpenAPIController`` 的实现。
2. 使用 `OpenAPIConfig.render_plugins` 属性配置 OpenAPI UI。如果未指定插件，系统会自动添加 `ScalarRenderPlugin` 作为默认配置。
3. 使用 `OpenAPIConfig.openapi_router` 属性进行额外配置。

更多信息请参阅 :doc:`/usage/openapi/ui_plugins`。

端点配置变更
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

3.0.0 版本不再提供 `OpenAPIConfig.enabled_endpoints` 属性。此前该属性用于启用不同的 OpenAPI UI 端点。新版本仅默认启用 `openapi.json` 端点和 `Scalar` UI 插件。

如需额外端点，请在 `OpenAPIConfig.render_plugins` 参数中正确设置所需插件。

`root_schema_site` 处理方式变更
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

3.0 版本移除了 `root_schema_site` 属性（该属性用于在 OpenAPI 根路径提供特定 UI）。新方法自动将 :attr:`OpenAPIConfig.render_plugins` 列表中的第一个 :class:`OpenAPIRenderPlugin` 分配到 ``/schema`` 端点，除非某个插件定义了根路径（``/``），在这种情况下将使用该插件。

对于之前使用 `root_schema_site` 属性的用户，迁移时需确保要在 ``/schema`` 端点提供的 UI 是 :attr:`OpenAPIConfig.render_plugins` 中列出的第一个插件。


移除 ``Response.to_asgi_response`` 的弃用参数 ``app``
-------------------------------------------------------------------------------

:meth:`~response.Response.to_asgi_response` 的参数 ``app`` 已被移除。
如果你需要在自定义的 ``to_asgi_response`` 方法中访问应用实例，
请将 ``app`` 的用法替换为 ``request.app``。


移除弃用的作用域状态工具
----------------------------------------

Litestar 之前提供了在 ASGI 作用域状态中存储和检索数据的工具。这些工具已在 3.0.0 版本中被移除。如果你需要在 ASGI 作用域状态中存储数据，应该使用对你的应用程序唯一且不太可能与其他应用程序冲突的命名空间。

以下工具已被移除：

- ``get_litestar_scope_state``
- ``set_litestar_scope_state``
- ``delete_litestar_scope_state``


移除弃用的工具函数 ``is_sync_or_async_generator``
------------------------------------------------------------------

工具函数 ``is_sync_or_async_generator`` 已被移除，因为内部不再使用。

如果你依赖此工具，可以自行定义如下：

.. code-block:: python

    from inspect import isasyncgenfunction, isgeneratorfunction

    def is_sync_or_async_generator(obj: Any) -> bool:
        return isgeneratorfunction(obj) or isasyncgenfunction(obj)


移除语义化 HTTP 路由处理器类
-----------------------------------------------

语义化 ``HTTPRouteHandler`` 类已被移除，改为使用函数装饰器。``route``、``get``、``post``、``patch``、``put``、``head`` 和 ``delete``
现在都是返回 :class:`~.handlers.HTTPRouteHandler` 实例的装饰器函数。

因此，不再能直接自定义装饰器。相反，要使用带有自定义路由处理器类的路由处理器装饰器，可以使用装饰器函数的 ``handler_class`` 参数：

之前：

.. code-block:: python

    class my_get_handler(get):
        ... # 自定义处理器

    @my_get_handler()
    async def handler() -> Any:
        ...

之后：

.. code-block:: python

    class MyHTTPRouteHandler(HTTPRouteHandler):
        ... # 自定义处理器


    @get(handler_class=MyHTTPRouteHandler)
    async def handler() -> Any:
        ...


移除弃用的 ``litestar.middleware.exceptions`` 模块和 ``ExceptionHandlerMiddleware``
--------------------------------------------------------------------------------------------------

弃用的 ``litestar.middleware.exceptions`` 模块和 ``ExceptionHandlerMiddleware`` 已被移除。由于 ``ExceptionHandlerMiddleware`` 在必要时会自动在后台应用，因此不需要采取任何操作。


更新 MessagePack 媒体类型为 ``application/vnd.msgpack``
------------------------------------------------------------

将 ``MessagePack`` 的默认媒体类型从 ``application/x-msgpack`` 更改为新引入的官方 ``application/vnd.msgpack``。

https://www.iana.org/assignments/media-types/application/vnd.msgpack


弃用路由处理器上的 ``resolve_`` 方法
-------------------------------------------------

路由处理器上的所有 ``resolve_`` 方法（例如 ``HTTPRouteHandler.resolve_response_headers``）已被弃用，并将在 ``4.0`` 中移除。现在可以安全地直接访问这些属性（例如 `HTTPRouteHandlers.response_headers`）。


将路由相关方法从 ``Router`` 移至 ``Litestar``
-------------------------------------------------------------

:class:`~litestar.router.Router` 现在只保存路由处理器和配置，而实际路由在 :class:`~litestar.app.Litestar` 中完成。因此，几个方法和属性已从 ``Router`` 移至 ``Litestar``：

- ``route_handler_method_map``
- ``get_route_handler_map``
- ``routes``


移除 ``CLIPluginProtocol``
---------------------------------

:class:`~typing.Protocol` ``CLIPluginProtocol`` 已被移除，改为抽象类 ``CLIPluginProtocol``。功能和接口保持不变，唯一区别是希望提供此功能的插件现在需要继承自 :class:`~.plugins.CLIPlugin`。


移除 ``OpenAPISchemaPluginProtocol``
------------------------------------------

:class:`~typing.Protocol` ``OpenAPISchemaPluginProtocol`` 已被移除，改为抽象类 :class:`~litestar.plugins.OpenAPISchemaPlugin`。功能和接口保持不变，唯一区别是希望提供此功能的插件现在需要继承自 :class:`~.plugins.OpenAPISchemaPlugin`。


放弃对 starlette 中间件协议的支持
-------------------------------------------------

不再支持 `starlette 中间件协议 <https://www.starlette.io/middleware>`_。

现在只支持"工厂"模式，即接收 ASGI 可调用对象作为唯一参数并返回另一个 ASGI 可调用对象的可调用对象：

.. code-block:: python

    def middleware(app: ASGIApp) -> ASGIApp:
        ...


.. seealso::
    :doc:`/usage/middleware/index`


移除 ``SerializationPluginProtocol``
------------------------------------------

:class:`~typing.Protocol` ``SerializationPluginProtocol`` 已被移除，改为抽象类 :class:`~litestar.plugins.SerializationPlugin`。功能和接口保持不变，唯一区别是希望提供此功能的插件现在需要继承自 :class:`~.plugins.SerializationPlugin`。


移除流式响应中的 ``body``
-------------------------------------------

:class:`~.ASGIStreamingResponse` 和 :class:`.ASGIFileResponse` 中不受支持的 ``body`` 参数已被移除。

这不会改变任何行为，因为此参数之前被忽略。


从默认依赖项中移除 ``polyfactory`` 包
----------------------------------------------------------

`polyfactory <https://polyfactory.litestar.dev/>`_ 库已从默认依赖项移至 ``litestar[polyfactory]`` 包额外项。它也包含在 ``litestar[full]`` 中。


从默认依赖项中移除 ``pyyaml`` 包
----------------------------------------------------

`PyYAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_ 库（用于将 OpenAPI 模式渲染为 YAML）已从默认依赖项移至 ``litestar[yaml]`` 包额外项。


从默认依赖项中移除 ``litestar-htmx`` 包
-----------------------------------------------------------

支持 :doc:`HTMX 插件 </usage/htmx>` 的 `litestar-htmx <https://github.com/litestar-org/litestar-htmx/>`_ 包已移至 ``litestar[htmx]`` 额外项。


改进的文件系统处理 / fsspec 集成
---------------------------------------------------

添加了更连贯的 :doc:`文件系统 </usage/file_systems>` 集成，改进了对 `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ 的支持。这个新实现更稳定、高效和一致，并包含新功能，如对所有支持的文件系统的随机访问以及流式传输（可选地带偏移量，即使底层文件系统不原生支持）。

.. seealso::
    :doc:`/usage/file_systems`


移除 ``create_static_files_router`` 的 ``resolve_symlinks`` 参数
---------------------------------------------------------------------------

:func:`~litestar.static_files.create_static_files_router` 的 ``resolve_symlinks`` 参数已被移除，改为新的 :paramref:`~litestar.static_files.create_static_files_router.allow_symlinks_outside_directory` 参数。

.. attention::
    这被有意设计为破坏性更改，因为新参数具有略微不同的行为，默认值为 ``False`` 而非 ``True``。


中间件配置约束
-------------------------------------

:class:`~litestar.middleware.ASGIMiddleware`\ 现在可以表达它们如何应用在中间件栈中的约束，这些约束会在应用启动时进行验证。

.. seealso::

    :ref:`usage/middleware/creating-middleware:配置约束`
