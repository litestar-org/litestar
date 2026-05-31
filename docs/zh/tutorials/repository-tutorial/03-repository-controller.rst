使用控制器和仓储
-----------------------------------------
我们一直在沿着堆栈向上工作,从数据库模型开始,现在我们准备在实际路由中使用仓储。让我们看看如何在控制器中使用它。

.. tip:: 本教程的完整代码可以在下面的 :ref:`完整代码 <03-repo-full-code>` 部分找到。

首先,我们创建一个简单的函数,返回 ``AuthorRepository`` 的实例。
此函数将用于将仓储实例注入到我们的控制器路由中。
请注意,在此示例中,我们仅传入数据库会话,没有其他参数。

.. literalinclude:: /examples/sqla/sqlalchemy_async_repository.py
    :language: python
    :caption: ``app.py``
    :lines: 82-84
    :linenos:

因为我们将在 Litestar 中使用 SQLAlchemy 插件,所以会话会自动配置为依赖项。

默认情况下,仓储不会向你的基本语句添加任何额外的查询选项,但提供了覆盖它的灵活性,允许你传递自己的语句:

.. literalinclude:: /examples/sqla/sqlalchemy_async_repository.py
    :language: python
    :caption: ``app.py``
    :lines: 87-94
    :linenos:

在这种情况下,我们通过添加 ``selectinload`` 选项来增强仓储函数。此选项将指定的关系配置为通过 `SELECT .. IN ...` 加载模式加载,优化查询执行。

接下来,我们定义 ``AuthorController``。此控制器公开五个用于与 ``Author`` 模型交互的路由:

.. dropdown:: ``AuthorController``(点击切换)

    .. literalinclude:: /examples/sqla/sqlalchemy_async_repository.py
        :language: python
        :caption: ``app.py``
        :lines: 120-199
        :linenos:

在我们的列表详细信息端点中,我们使用分页过滤器来限制返回的数据量,允许我们以更小、更易于管理的块检索大型数据集。

在上面的示例中,我们使用了异步仓储实现。然而,Litestar 也支持具有相同实现的同步数据库驱动程序。
这是前面示例的相应同步版本:

.. dropdown:: 同步仓储(点击切换)

    .. literalinclude:: /examples/sqla/sqlalchemy_sync_repository.py
        :language: python
        :caption: ``app.py``
        :linenos:

上面的示例启用了一个功能完整的 CRUD 服务,包括分页!在下一节中,我们将探讨如何扩展内置仓储以向我们的应用程序添加其他功能。

.. _03-repo-full-code:

完整代码
---------

.. dropdown:: 完整代码(点击切换)

    .. literalinclude:: /examples/sqla/sqlalchemy_async_repository.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 82-84, 87-94, 120-199
        :linenos:
