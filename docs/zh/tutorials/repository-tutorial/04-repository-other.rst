为仓储添加其他功能
--------------------------------------------

虽然你需要的大多数功能都内置在仓储中,但仍然存在你需要添加其他功能的情况。让我们探讨一下如何在仓储模式之上添加功能的方法。

.. tip:: 本教程的完整代码可以在下面的 :ref:`完整代码 <04-repo-full-code>` 部分找到。

Slug 字段
-----------

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 10-23, 33-34, 37-42, 101-102, 106-108
    :linenos:

在这个示例中,我们使用 ``BlogPost`` 模型来保存博客文章标题和内容。此模型的主键是 ``UUID`` 类型。``UUID`` 和 ``int`` 是主键的良好选择,但你可能不想在路由中使用它们有许多原因。例如,在 URL 中暴露基于整数的主键可能存在安全问题。虽然 UUID 没有这个问题,但它们不是用户友好的或易于记忆的,并创建复杂的 URL。解决此问题的一种方法是向表中添加用户友好的唯一标识符,可用于 URL。这通常称为"slug"。

首先,我们将创建一个 ``SlugKey`` 字段混入,它向表中添加基于文本的、URL 友好的、唯一列 ``slug``。我们希望确保根据传递给 ``title`` 字段的数据创建 slug 值。为了演示我们试图实现的目标,我们希望博客标题为"Follow the Yellow Brick Road!"的记录具有"follow-the-yellow-brick-road"的 slugified 值。

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 1-8, 14-23, 43-44, 46-100
    :linenos:

由于 ``BlogPost.title`` 字段未标记为唯一,这意味着我们必须在插入之前测试 slug 值的唯一性。如果找到初始 slug,则会在 slug 末尾附加一组随机数字以使其唯一。

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 1-23, 27-32, 101-102, 106-126, 170-180
    :linenos:

我们现在已准备好在路由中使用它。首先,我们将传入的 Pydantic 模型转换为字典。接下来,我们将为文本获取唯一的 slug。最后,我们使用添加的 slug 插入模型。

.. note::

    使用此方法会在每次插入时引入额外的查询。在确定哪些字段实际需要此类功能时应考虑这一点。

.. _04-repo-full-code:

完整代码
---------

.. dropdown:: 完整代码(点击切换)

    .. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 12, 37-42, 106-108, 177
        :linenos:
