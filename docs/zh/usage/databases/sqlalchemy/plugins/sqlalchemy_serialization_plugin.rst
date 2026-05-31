SQLAlchemy 序列化插件
-------------------------------

SQLAlchemy 序列化插件允许 Litestar 完成将入站和出站数据与 SQLAlchemy 模型之间转换的工作。该插件不需要参数，只需实例化它并将其传递给您的应用程序即可。

示例
=======

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin.py
            :caption: SQLAlchemy 异步序列化插件
            :language: python
            :linenos:

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_serialization_plugin.py
            :caption: SQLAlchemy 同步序列化插件
            :language: python
            :linenos:

工作原理
============

该插件通过为每个处理程序 ``data`` 或返回注解定义 :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` 类来工作，这些注解是 SQLAlchemy 模型或 SQLAlchemy 模型的集合，并且没有由显式定义的 DTO 类管理。

以下两个示例在功能上是等效的：

.. tab-set::

   .. tab-item:: 序列化插件

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin.py
            :language: python
            :linenos:

   .. tab-item:: 数据传输对象

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_dto.py
            :language: python
            :linenos:

在注册期间，应用程序识别到没有显式定义 DTO 类，并确定处理程序注解由 SQLAlchemy 序列化插件支持。然后使用该插件为 ``data`` 关键字参数和返回注解生成 DTO 类。

配置数据传输
#########################

由于序列化插件仅为处理程序定义 DTO，我们可以 :ref:`标记模型字段 <dto-marking-fields>` 来控制我们允许进出应用程序的数据。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin_marking_fields.py
            :caption: SQLAlchemy 异步标记字段
            :language: python
            :linenos:
            :emphasize-lines: 10,23

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_serialization_plugin_marking_fields.py
            :caption: SQLAlchemy 同步标记字段
            :language: python
            :linenos:
            :emphasize-lines: 10,23

在上面的示例中，一个名为 ``super_secret_value`` 的新属性已添加到模型中，并在处理程序中为其设置了一个值。但是，由于将字段"标记"为"私有"，当模型序列化时，该值不会出现在响应中。
