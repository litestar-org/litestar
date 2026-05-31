从嵌套模型集合中排除
-------------------------------------------

在 Python 中,泛型类型可以接受一个或多个类型参数(包含在方括号中的类型)。当表示某种类型的集合时,经常会看到这种模式,例如 ``List[Person]``,其中 ``List`` 是泛型容器类型,``Person`` 将集合的内容专门化为仅包含 ``Person`` 类的实例。

给定一个具有任意数量类型参数的泛型类型(例如,``GenericType[Type0, Type1, ..., TypeN]``),我们使用类型参数的索引来指示排除应引用哪种类型。例如,``a.0.b`` 从 ``a`` 的第一个类型参数中排除 ``b`` 字段,``a.1.b`` 从 ``a`` 的第二个类型参数中排除 ``b`` 字段,依此类推。

为了演示,让我们向 ``Person`` 模型添加一个自引用的 ``children`` 关系:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/nested_collection_exclude.py
   :language: python
   :linenos:
   :emphasize-lines: 22,26,34,35,41

现在,一个 ``Person`` 可以有一个或多个 ``children``,每个 ``child`` 可以有一个或多个 ``children``,依此类推。

我们明确排除了所有表示的 ``children`` 的 ``email`` 和 ``address`` 字段(``"children.0.email", "children.0.address"``)。

在我们的处理器中,我们向 ``Person`` 添加 ``children``,每个子代没有自己的 ``children``。

输出如下:

.. image:: images/nested_collection_exclude.png
    :align: center

太棒了!我们的 ``children`` 现在在输出中表示,并且排除了他们的电子邮件和地址。但是,敏锐的读者可能已经注意到我们没有排除 ``Person.children`` 的 ``children`` 字段(例如,``children.0.children``),但该字段未在输出中表示。要理解原因,我们接下来将查看 :attr:`max_nested_depth <litestar.dto.config.DTOConfig.max_nested_depth>` 配置选项。
