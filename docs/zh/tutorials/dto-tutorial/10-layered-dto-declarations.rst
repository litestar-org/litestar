在应用层上声明 DTO
-----------------------------

到目前为止,我们已经看到每个处理器声明的 DTO。让我们看看一个声明多个处理器的脚本 - 这在真实应用程序中更典型。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/multiple_handlers.py
   :language: python
   :linenos:

DTO 可以在应用程序的任何 :ref:`层 <layered-architecture>` 上定义,这使我们有机会整理一下代码。让我们将处理器移到控制器中并在那里定义 DTO。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/controller.py
   :language: python
   :linenos:
   :emphasize-lines: 30,31,44

先前的脚本为每个路由都有单独的处理器函数,而新脚本将这些组织到 ``PersonController`` 类中,允许我们将通用配置移至控制器层。

我们在 ``PersonController`` 类上定义了 ``dto=WriteDTO`` 和 ``return_dto=ReadDTO``,消除了在每个处理器上定义这些的需要。我们仍然直接在 ``patch_person`` 处理器上定义 ``PatchDTO``,以覆盖该处理器的控制器级别 ``dto`` 设置。
