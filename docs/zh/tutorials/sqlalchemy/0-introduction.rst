简介
------------

我们从一个完整的脚本开始,展示如何将 SQLAlchemy 与 Litestar 一起使用。在这个应用程序中,我们以 `SQLAlchemy 文档 <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-orm>`_ 中描述的方式与 SQLAlchemy 交互,因此,如果你正在寻找有关任何 SQLAlchemy 代码的更多信息,这将是一个很好的起点。

你会注意到我们使用了一些你可能还没有遇到过的 Litestar 特性:

1. :ref:`应用程序状态 <application-state>` 的管理和注入
2. 使用 :ref:`生命周期上下文管理器 <lifespan-context-managers>`

随着我们在教程中的学习,我们将继续了解其他 Litestar 特性,例如:

1. 依赖注入
2. 插件

完整应用程序
============

虽然看起来可能令人生畏,但这个应用程序与之前的示例只有很小的行为差异。它仍然是一个维护 TODO 列表的应用程序,允许添加、更新和查看 TODO 项目的集合。

如果这个示例中有你不理解的内容,不要担心。我们将在后续部分详细介绍所有组件。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:

差异
===============

除了由于 SQLAlchemy 代码而产生的明显差异之外,还有一些值得从一开始就提及的事情。

复杂性
++++++++++

这段代码无疑比我们迄今为止看到的代码更复杂 - 尽管这是一个粗略的复杂性度量,但我们可以看到代码行数是之前示例的两倍多。

生命周期上下文管理器
++++++++++++++++++++++++

当使用数据库时,我们需要确保正确清理资源。为此,我们创建了一个名为 ``db_connection()`` 的上下文管理器,它创建一个新的 :class:`engine <sqlalchemy.ext.asyncio.AsyncEngine>` 并在完成时处理它。这个上下文管理器被添加到应用程序的 ``lifespan`` 参数中。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 28-41,100

数据库创建
+++++++++++++++++
在我们可以使用数据库之前,我们需要确保它存在并且表已按 ``TodoItem`` 类定义创建。这可以通过对 ``Base.metadata.create_all`` 的同步调用来完成,该调用由 ``run_sync`` 调用。如果表已根据模型设置,则该调用不执行任何操作。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 28-41
    :emphasize-lines: 8-9

应用程序状态
+++++++++++++++++

我们看到两个访问和使用应用程序状态的示例。第一个是在 ``db_connection()`` 上下文管理器中,我们使用 ``app.state`` 对象来存储引擎。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 28-41
    :emphasize-lines: 3,6

第二个是在我们的处理器函数中使用 ``state`` 关键字参数,以便我们可以在处理器中访问引擎。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 69-72
    :emphasize-lines: 2,3

序列化
+++++++++++++

现在我们使用 SQLAlchemy 模型,Litestar 无法自动处理数据的(反)序列化。我们必须将 SQLAlchemy 模型转换为 Litestar 可以序列化的类型。这个示例引入了两个类型别名,``TodoType`` 和 ``TodoCollectionType`` 来帮助我们在处理器的边界表示这些数据。它还引入了 ``serialize_todo()`` 来帮助我们将数据从 ``TodoItem`` 类型转换为 Litestar 可以序列化的类型。

.. literalinclude::
    /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 2-3,14-15,47-50,91-98
    :emphasize-lines: 3,6,10,15

行为
++++++++

``add_item()`` 和 ``update_item()`` 路由不再返回完整集合,而是返回添加或更新的项目。这是一个细微的细节变化,但值得注意,因为它使应用程序的行为更接近我们从传统 API 中期望的行为。

下一步
==========

让我们开始稍微清理一下这个应用程序。

一个突出的问题是我们在每个处理器中重复创建数据库会话的逻辑。这是我们可以通过依赖注入来解决的问题。
