最大嵌套深度
----------------

正如我们在上一节中看到的,即使我们没有明确从嵌套的 ``Person.children`` 表示中排除 ``children``,它们也没有包含在响应中。

这是输出的提醒:

.. image:: images/nested_collection_exclude.png
    :align: center

鉴于我们没有明确地从响应中排除它,``children`` 集合中的每个 ``Person`` 对象都应该有一个空的 ``children`` 集合。它们没有的原因是由于 :attr:`max_nested_depth <litestar.dto.config.DTOConfig.max_nested_depth>` 及其默认值 ``1``。

``max_nested_depth`` 属性用于限制响应中包含的嵌套对象的深度。在这种情况下,``Person`` 对象有一个 ``children`` 集合,它是嵌套 ``Person`` 对象的集合,因此这代表嵌套深度为 1。``Person.children`` 集合中项目的 ``children`` 集合处于第二级嵌套,因此由于 ``max_nested_depth`` 的默认值而被排除。

现在让我们修改脚本以在响应中包含子代的子代:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/max_nested_depth.py
   :language: python
   :linenos:
   :emphasize-lines: 28

我们现在在输出中看到那些空集合:

.. image:: images/max_nested_depth.png
    :align: center

现在我们已经了解了如何使用 ``max_nested_depth`` 配置,在本教程的其余部分,我们将恢复使用默认值 ``1``。
