.. _updating:

更新实例
------------------

在本节中,我们将了解如何使用 :class:`DTOData <litestar.dto.data_structures.DTOData>` 更新现有实例。

PUT 处理器
============

`PUT <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT>`_ 请求的特点是需要提交完整的数据模型进行更新。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/put_handlers.py
   :language: python
   :linenos:
   :emphasize-lines: 25,28,29

此脚本定义了一个路径为 ``/person/{person_id:int}`` 的 ``PUT`` 处理器,其中包含一个路由参数 ``person_id`` 来指定应该更新哪个人。

在处理器中,我们创建一个 ``Person`` 实例,模拟数据库查找,然后将其传递给 :meth:`DTOData.update_instance() <litestar.dto.data_structures.DTOData.update_instance>` 方法,该方法在使用提交的数据修改实例后返回相同的实例。

.. image:: images/put_handlers.png
    :align: center

PATCH 处理器
==============

`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ 请求的特点是允许提交数据模型的任何属性子集进行更新。这与 `PUT <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT>`_ 请求形成对比,后者需要提交整个数据模型。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/patch_handlers.py
   :language: python
   :linenos:
   :emphasize-lines: 21,22,25

在这个最新更新中,处理器已更改为 :class:`@patch() <litestar.handlers.patch>` 处理器。

此脚本引入了 ``PatchDTO`` 类,它具有与 ``WriteDTO`` 类似的配置,排除了 ``id`` 字段,但它还设置了 :attr:`partial=True <litestar.dto.config.DTOConfig.partial>`。此设置允许对资源进行部分更新。

这是使用演示:

.. image:: images/patch_handlers.png
    :align: center
