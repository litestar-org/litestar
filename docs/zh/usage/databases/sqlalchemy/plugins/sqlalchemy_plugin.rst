SQLAlchemy 插件
-----------------

:class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyPlugin>` 为在 Litestar 应用程序中使用 `SQLAlchemy <https://www.sqlalchemy.org/>`_ 提供完整支持。

.. note::

    此插件仅与 SQLAlchemy 2.0+ 兼容。

:class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyPlugin>` 结合了 :class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyInitPlugin>` 和 :class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin>` 的功能，每个插件都在以下部分中详细介绍。因此，本节描述了一个使用 :class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyPlugin>` 与 Litestar 应用程序和 SQLite 数据库的完整示例。

或者，跳到 :doc:`/usage/databases/sqlalchemy/plugins/sqlalchemy_init_plugin` 或 :doc:`/usage/databases/sqlalchemy/plugins/sqlalchemy_serialization_plugin` 以了解有关各个插件的更多信息。

.. tip::

    您可以通过运行 ``pip install 'litestar[sqlalchemy]'`` 将 SQLAlchemy 与 Litestar 一起安装。

示例
=======

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_plugin_example.py
            :caption: SQLAlchemy 异步插件示例
            :language: python
            :linenos:

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_plugin_example.py
            :caption: SQLAlchemy 同步插件示例
            :language: python
            :linenos:

定义数据库模型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

我们首先定义基础模型类和扩展基础模型的 ``TodoItem`` 类。``TodoItem`` 类表示 SQLite 数据库中的待办事项。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_plugin_example.py
            :caption: SQLAlchemy 异步插件示例
            :language: python
            :lines: 6,15-24

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_plugin_example.py
            :caption: SQLAlchemy 同步插件示例
            :language: python
            :lines: 6,15-24

设置 API 端点
~~~~~~~~~~~~~~~~~~~~~~~~~~

接下来，我们在根路径 (``"/"``) 设置一个 API 端点，允许将 ``TodoItem`` 添加到 SQLite 数据库。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_plugin_example.py
            :caption: SQLAlchemy 异步插件示例
            :language: python
            :lines: 3-5,8,10-14,25-31

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_plugin_example.py
            :caption: SQLAlchemy 同步插件示例
            :language: python
            :lines: 3-5,8,10-14,25-31

初始化数据库
~~~~~~~~~~~~~~~~~~~~~~~~~

我们创建一个 ``init_db`` 函数，用于在应用程序启动时初始化数据库。

.. important::

    在此示例中，我们在创建数据库之前删除数据库。这样做是为了可重复性，不应在生产环境中这样做。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_plugin_example.py
            :caption: SQLAlchemy 异步插件示例
            :language: python
            :lines: 9,31-35

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_plugin_example.py
            :caption: SQLAlchemy 同步插件示例
            :language: python
            :lines: 9,31-33

设置插件和应用程序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

最后，我们设置 SQLAlchemy 插件和 Litestar 应用程序。

.. tab-set::

   .. tab-item:: 异步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_plugin_example.py
            :caption: SQLAlchemy 异步插件示例
            :language: python
            :lines: 8,31-35

   .. tab-item:: 同步

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_plugin_example.py
            :caption: SQLAlchemy 同步插件示例
            :language: python
            :lines: 9,31-33

这将使用插件配置应用程序，为添加项目设置路由处理程序，并指定在应用程序启动时运行 ``init_db`` 函数。

运行应用程序
~~~~~~~~~~~~~~~

使用以下命令运行应用程序：

.. code-block:: bash

    $ litestar run

您现在可以通过向 ``http://localhost:8000`` 发送 POST 请求来添加待办事项，请求的 JSON 正文应包含待办事项的 ``"title"``。

.. code-block:: bash

    $ curl -X POST -H "Content-Type: application/json" -d '{"title": "Your Todo Title", "done": false}' http://localhost:8000/
