访问数据
------------------

有时,立即将数据解析为目标类的实例是没有意义的。我们刚刚在前一节 :ref:`read-only-fields` 中看到了一个例子。当必需字段从客户端提交的数据中排除或不存在时,我们将在实例化类时收到错误。

解决此问题的方法是 :class:`DTOData <litestar.dto.data_structures.DTOData>` 类型。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/dto_data.py
   :language: python
   :linenos:
   :emphasize-lines: 6,26,28

:class:`DTOData <litestar.dto.data_structures.DTOData>` 类型是可用于创建实例并访问底层解析和验证数据的数据容器。在我们的最新调整中,我们从 ``litestar.dto.factory`` 导入它。

处理器函数的数据参数类型更改为 ``DTOData[Person]`` 而不是 ``Person``,相应地,注入以表示入站客户端数据的值将是 :class:`DTOData <litestar.dto.data_structures.DTOData>` 的实例。

在处理器中,我们为 ``id`` 字段生成一个值,并使用 ``DTOData`` 实例的 :meth:`create_instance <litestar.dto.data_structures.DTOData.create_instance>` 方法创建 ``Person`` 的实例。

我们的应用程序恢复到工作状态:

.. image:: images/dto_data.png
    :align: center

.. tip::
    要为嵌套属性提供值,你可以使用"双下划线"语法作为 :meth:`create_instance() <litestar.dto.data_structures.DTOData.create_instance>` 方法的关键字参数。例如,``address__id=1`` 将设置创建实例的 ``address`` 属性的 ``id`` 属性。

    有关更多信息,请参阅 :ref:`dto-create-instance-nested-data`。

:class:`DTOData <litestar.dto.data_structures.DTOData>` 类型还有一些其他有用的方法,我们将在下一节中查看这些方法::ref:`updating`。
