SQLAlchemy 初始化插件
----------------------

:class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyInitPlugin>` 为应用程序添加功能，支持将 Litestar 与 `SQLAlchemy <http://www.sqlalchemy.org/>`_ 一起使用。

该插件：

- 通过依赖注入使 SQLAlchemy 引擎和会话可用。
- 在应用程序的状态中管理 SQLAlchemy 引擎和会话工厂。
- 配置在发送响应之前调用的 ``before_send`` 处理程序。
- 在签名命名空间中包含相关名称以帮助解析注解类型。

依赖项
============

该插件使引擎和会话可用于注入。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_dependencies.py
            :caption: SQLAlchemy 异步依赖项
            :language: python
            :linenos:

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_dependencies.py
            :caption: SQLAlchemy 同步依赖项
            :language: python
            :linenos:

上面的示例说明了如何在处理程序中访问引擎和会话，与所有其他依赖项一样，它们也可以注入到其他依赖函数中。

重命名依赖项
#########################

您可以通过在插件配置上设置 :attr:`engine_dependency_key <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.engine_dependency_key>` 和 :attr:`session_dependency_key <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.session_dependency_key>` 属性来更改引擎和会话绑定的名称。

配置发送前处理程序
###################################

该插件配置在发送响应之前调用的 ``before_send`` 处理程序。默认处理程序关闭会话并将其从连接范围中删除。

您可以通过在配置对象上设置 :attr:`before_send_handler <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.before_send_handler>` 属性来更改处理程序。例如，有一个替代处理程序可用，它将在成功时提交会话并在失败时回滚。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_before_send_handler.py
            :caption: SQLAlchemy 异步发送前处理程序
            :language: python
            :linenos:

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_before_send_handler.py
            :caption: SQLAlchemy 同步发送前处理程序
            :language: python
            :linenos:

配置插件
#######################

:class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` 和 :class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` 都有一个 ``engine_config`` 属性，用于配置引擎。``engine_config`` 属性是 :class:`EngineConfig <advanced_alchemy.extensions.litestar.EngineConfig>` 的实例，并公开 SQLAlchemy 引擎可用的所有配置选项。

:class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` 类和 :class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` 类还有一个 ``session_config`` 属性，用于配置会话。根据配置对象的类型，这是 :class:`AsyncSessionConfig <advanced_alchemy.extensions.litestar.AsyncSessionConfig>` 或 :class:`SyncSessionConfig <advanced_alchemy.extensions.litestar.SyncSessionConfig>` 的实例。这些类公开 SQLAlchemy 会话可用的所有配置选项。

最后，:class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` 类和 :class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` 类公开配置选项以控制其行为。

有关更多信息，请参阅参考文档。

示例
=======

下面的示例是初始化插件使用的完整演示。熟悉前面部分的读者可能会注意到在处理程序中管理与 SQLAlchemy 对象之间的转换所涉及的额外复杂性。继续阅读以了解 :class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin>` 如何有效地处理这种增加的复杂性。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_init_plugin_example.py
            :caption: SQLAlchemy 异步初始化插件示例
            :language: python
            :linenos:

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_init_plugin_example.py
            :caption: SQLAlchemy 同步初始化插件示例
            :language: python
            :linenos:
