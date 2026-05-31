.. _plugins:

=======
插件
=======

Litestar 支持一个插件系统，允许您扩展框架的功能。


插件由协议定义，任何满足协议的类型都可以包含在 :class:`应用程序 <litestar.app.Litestar>` 的 ``plugins`` 参数中。


InitPlugin
----------

``InitPlugin`` 定义了一个接口，允许自定义应用程序的初始化过程。
初始化插件可以定义依赖项、添加路由处理程序、配置中间件等等！

这些插件的实现必须定义一个方法：
:meth:`on_app_init(self, app_config: AppConfig) -> AppConfig: <litestar.plugins.InitPlugin.on_app_init>`

该方法接受并必须返回一个 :class:`AppConfig <litestar.config.app.AppConfig>` 实例，该实例可以被修改，稍后用于实例化应用程序。

此方法在任何 ``on_app_init`` 钩子被调用后调用，并且每个插件按照它们在 :class:`应用程序 <litestar.app.Litestar>` 的 ``plugins`` 参数中提供的顺序调用。因此，插件作者应在其文档中明确说明其插件应在其他插件之前还是之后调用。

示例
+++++++

以下示例展示了一个简单的插件，它向应用程序添加路由处理程序和依赖项。

.. literalinclude:: /examples/plugins/init_plugin_protocol.py
   :language: python
   :caption: ``InitPlugin`` 实现示例

``MyPlugin`` 类是 :class:`InitPlugin <litestar.plugins.InitPlugin>` 的实现。它定义了一个方法 ``on_app_init()``，该方法接受一个 :class:`AppConfig <litestar.config.app.AppConfig>` 实例作为参数并返回相同实例。

在 ``on_app_init()`` 方法中，依赖项映射被更新以包含一个名为 ``"name"`` 的新依赖项，该依赖项由 ``get_name()`` 函数提供，并且 ``route_handlers`` 被更新以包含 ``route_handler()`` 函数。然后返回修改后的 :class:`AppConfig <litestar.config.app.AppConfig>` 实例。

SerializationPlugin
---------------------------

:class:`~litestar.plugins.SerializationPlugin` 为框架原本不支持的数据类型提供序列化功能的插件定义了一个契约。

这些插件的实现必须定义以下方法。

1. :meth:`supports_type(self, field_definition: FieldDefinition) -> bool: <litestar.plugins.SerializationPlugin>`

该方法接受一个 :class:`FieldDefinition <litestar.typing.FieldDefinition>` 实例作为参数，并返回一个 :class:`bool`，指示插件是否支持该类型的序列化。

2. :meth:`create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]: <litestar.plugins.SerializationPlugin.create_dto_for_type>`

该方法接受一个 :class:`FieldDefinition <litestar.typing.FieldDefinition>` 实例作为参数，并且必须返回一个 :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` 实现，可用于序列化和反序列化该类型。

在应用程序启动期间，如果遇到不受支持的数据或返回注解类型，但插件支持该类型，并且没有另外定义 ``dto`` 或 ``return_dto``，则使用插件为该注解创建 DTO 类型。

示例
+++++++

以下示例展示了针对 `SQLAlchemy <https://www.sqlalchemy.org/>`_ 模型的 ``SerializationPlugin`` 的实现模式。有关实际实现，请参阅 ``advanced_alchemy`` 库文档。

:meth:`supports_type(self, field_definition: FieldDefinition) -> bool: <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin.supports_type>` 返回一个 :class:`bool`，指示插件是否支持给定类型的序列化。具体来说，如果解析的类型是 SQLAlchemy 模型的集合或单个 SQLAlchemy 模型，我们返回 ``True``。

:meth:`create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]: <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin.create_dto_for_type>` 接受一个 :class:`FieldDefinition <litestar.typing.FieldDefinition>` 实例作为参数，并返回一个 :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` 子类，并包含一些对潜在序列化插件作者可能有趣的逻辑。

该方法首先检查解析的类型是 SQLAlchemy 模型的集合还是单个 SQLAlchemy 模型，在任一情况下检索模型类型并将其分配给 ``annotation`` 变量。

然后，该方法检查 ``annotation`` 是否已在 ``_type_dto_map`` 字典中。如果是，则返回相应的 DTO 类型。这样做是为了确保不会为同一模型创建多个 :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` 子类型。

如果注解不在 ``_type_dto_map`` 字典中，该方法为注解创建一个新的 DTO 类型，将其添加到 ``_type_dto_map`` 字典中，并返回它。


DIPlugin
--------

:class:`~litestar.plugins.DIPlugin` 可用于通过提供有关可注入类型的信息来扩展 Litestar 的依赖注入。

其主要目的是促进具有未知签名的可调用对象的注入，例如 Pydantic 的 ``BaseModel`` 类；这些原生不受支持，因为虽然它们是可调用的，但它们的类型信息不包含在它们的可调用签名中（它们的 :func:`__init__` 方法）。


.. literalinclude:: /examples/plugins/di_plugin.py
   :language: python
   :caption: 为自定义类型动态生成签名信息

.. toctree::
    :titlesonly:

    flash_messages
    problem_details


ReceiveRoutePlugin
------------------

:class:`~litestar.plugins.ReceiveRoutePlugin` 允许您在路由注册到应用程序时接收路由。这对于需要根据添加的路由执行操作的插件很有用，例如生成文档、验证路由配置或跟踪路由统计信息。

此插件的实现必须定义一个方法：
:meth:`receive_route(self, route: BaseRoute) -> None: <litestar.plugins.ReceiveRoutePlugin.receive_route>`

该方法在路由注册到应用程序时接收一个 :class:`BaseRoute <litestar.routes.BaseRoute>` 实例。这发生在应用程序初始化过程中，在创建路由之后但在应用程序启动之前。

示例
+++++++

以下示例展示了一个简单的插件，它在注册每个路由时记录有关该路由的信息：

.. code-block:: python

    from litestar.plugins import ReceiveRoutePlugin
    from litestar.routes import BaseRoute

    class RouteLoggerPlugin(ReceiveRoutePlugin):
        def receive_route(self, route: BaseRoute) -> None:
            print(f"Route registered: {route.path} [{', '.join(route.methods)}]")
