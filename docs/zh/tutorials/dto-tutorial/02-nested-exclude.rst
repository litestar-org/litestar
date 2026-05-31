从嵌套模型中排除
----------------------------

``exclude`` 选项可用于通过使用点路径从与我们的数据模型相关的模型中排除字段。例如,``exclude={"a.b"}`` 将排除嵌套在 ``a`` 属性上的实例的 ``b`` 属性。

为了演示,让我们调整脚本以添加与 ``Person`` 模型相关的 ``Address`` 模型:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/nested_exclude.py
   :language: python
   :linenos:
   :emphasize-lines: 9-13,21,25,32,33

``Address`` 模型有三个属性:``street``、``city`` 和 ``country``,我们向 ``Person`` 模型添加了一个 ``address`` 属性。

``ReadDTO`` 类已更新为使用点路径语法 ``"address.street"`` 排除嵌套 ``Address`` 模型的 ``street`` 属性。

在处理器内部,我们创建一个 ``Address`` 实例并将其分配给 ``Person`` 的 ``address`` 属性。

当我们调用处理器时,我们可以看到 ``street`` 属性未包含在响应中:

.. image:: images/nested_exclude.png
    :align: center
