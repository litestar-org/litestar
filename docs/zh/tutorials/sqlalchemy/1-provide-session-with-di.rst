使用依赖注入提供会话
-----------------------------


在我们的原始脚本中,我们必须为每个请求类型重复构造会话实例的逻辑。这不是很 `DRY <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_。

在本节中,我们将使用依赖注入来集中会话创建逻辑,并使其可用于所有处理器。

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :emphasize-lines: 47-57,82-83,87-89,94-95,103

在前面的示例中,数据库会话是在每个 HTTP 路由处理器函数中创建的。在这个脚本中,我们使用依赖注入将会话的创建与路由处理器解耦。

这个脚本引入了一个新的异步生成器函数 ``provide_transaction()``,它创建一个新的 SQLAlchemy 会话,开始一个事务,并处理可能从事务中引发的任何完整性错误。

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 48-57

该函数使用名称 ``transaction`` 声明为 Litestar 应用程序的依赖项。

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 101-105
    :emphasize-lines: 3

在路由处理器中,通过将 ``transaction`` 名称声明为函数参数来注入数据库会话。这由 Litestar 的依赖注入系统在运行时自动提供。


.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 81-84
    :emphasize-lines: 2

这个脚本的最后一个改进是异常处理。在以前的版本中,如果在插入新 TODO 项目期间引发完整性错误,则在 ``add_item()`` 处理器内部引发 :class:`litestar.exceptions.ClientException`。在我们的最新版本中,我们已经能够集中这种处理,使其在 ``provide_transaction()`` 函数内部发生。

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 47-57
    :emphasize-lines: 3,6-10

此更改将异常处理的范围扩大到使用数据库会话的任何操作,而不仅仅是新项目的插入。

比较引入 DI 前后的处理器
====================================

只是为了好玩,让我们比较一下在为会话对象引入依赖注入之前和之后的应用程序处理器集:

.. tab-set::

   .. tab-item:: 之后

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
            :language: python
            :linenos:
            :lines: 81-105

   .. tab-item:: 之前

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
            :language: python
            :linenos:
            :lines: 69-100

好多了!

下一步
==========

我们失去的一个优点是能够以数据模型实例的形式从处理器接收和返回数据。在原始的 TODO 应用程序中,我们使用 Python 数据类进行建模,这些数据类由 Litestar 原生支持(反)序列化。在下一节中,我们将看看如何恢复这个功能!
