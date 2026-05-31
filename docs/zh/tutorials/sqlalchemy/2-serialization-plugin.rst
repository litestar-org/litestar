使用序列化插件
------------------------------

我们的下一个改进是利用
:class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemySerializationPlugin>`
以便我们可以直接从处理器接收和返回 SQLAlchemy 模型。

代码如下:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_serialization_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 12, 75-77, 80-83, 86-91, 98

我们只是导入了插件并将其添加到应用程序的插件列表中,现在我们可以直接从处理器接收和返回 SQLAlchemy 数据模型。

我们还能够删除 ``TodoType`` 和 ``TodoCollectionType`` 别名以及 ``serialize_todo()`` 函数,使实现更加简洁。

比较引入序列化插件前后的处理器
======================================================

再一次,让我们比较重构前后的应用程序处理器集:

.. tab-set::

   .. tab-item:: 之后

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_serialization_plugin.py
            :language: python
            :linenos:
            :lines: 1-13, 73-99

   .. tab-item:: 之前

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
            :language: python
            :linenos:
            :lines: 1-12, 67-100

非常好!但是,我们可以做得更好。

下一步
==========

在我们的应用程序中,我们必须构建一些脚手架来将 SQLAlchemy 与我们的应用程序集成。我们必须定义 ``db_connection()`` 生命周期上下文管理器和 ``provide_transaction()`` 依赖提供程序。

接下来我们将看看 :class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyInitPlugin>` 如何帮助我们。
