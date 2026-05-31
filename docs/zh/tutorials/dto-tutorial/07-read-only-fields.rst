.. _read-only-fields:

只读字段
----------------

有时,字段永远不应该由客户端指定。例如,在创建新资源实例时,模型的 ``id`` 字段应由服务器生成,而不是由客户端指定。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/read_only_fields_error.py
   :language: python
   :linenos:
   :emphasize-lines: 14

在此调整中,我们向 ``Person`` 模型添加一个 ``id`` 字段。我们还创建了一个新类 ``WriteDTO``,指示它忽略 ``id`` 属性。

``WriteDTO`` 类通过 ``dto`` kwarg(``dto=WriteDTO``)分配给处理器,这意味着在创建新的 ``Person`` 实例时,``id`` 字段将从从客户端接收的任何数据中被忽略。

当我们尝试创建指定了 ``id`` 字段的新 ``Person`` 实例时,我们会收到错误:

.. image:: images/read_only_fields_error.png
   :align: center

发生了什么?DTO 正在尝试构造 ``Person`` 模型的实例,但我们已从接受的客户端数据中排除了 ``id`` 字段。``Person`` 模型需要 ``id`` 字段,因此模型构造函数引发错误。

有多种方法可以解决此问题,例如我们可以为 ``id`` 字段分配默认值并在处理器中覆盖默认值,或者我们可以创建一个完全独立的没有 ``id`` 字段的模型,并在处理器中将数据从该模型传输到 ``Person`` 模型。但是,Litestar 为此提供了内置解决方案::class:`DTOData <litestar.dto.data_structures.DTOData>`。
