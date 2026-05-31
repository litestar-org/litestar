重命名字段
---------------

用于序列化的字段名称可以通过显式声明新名称或声明重命名策略来更改。

显式重命名字段
==========================

我们可以使用 :attr:`rename_fields <litestar.dto.config.DTOConfig.rename_fields>` 属性显式重命名字段。此属性是一个字典,将原始字段名称映射到新字段名称。

在此示例中,我们将 ``address`` 字段重命名为 ``location``:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/explicit_field_renaming.py
   :language: python
   :linenos:
   :emphasize-lines: 28

注意 ``address`` 字段如何重命名为 ``location``。

.. image:: images/explicit_field_renaming.png
    :align: center

字段重命名策略
=========================

除了显式重命名字段外,我们还可以使用字段重命名策略。

字段重命名策略使用 :attr:`rename_strategy <litestar.dto.config.DTOConfig.rename_strategy>` 配置指定。

Litestar 支持以下策略:

- ``lower``:将字段名称转换为小写
- ``upper``:将字段名称转换为大写
- ``camel``:将字段名称转换为驼峰式
- ``pascal``:将字段名称转换为帕斯卡式

.. note::

    你还可以通过传递一个接收字段名称并返回新字段名称的可调用对象到 ``rename_strategy`` 配置来定义自己的策略。

让我们修改示例以使用 ``upper`` 策略:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/field_renaming_strategy.py
   :language: python
   :linenos:
   :emphasize-lines: 28

结果如下:

.. image:: images/field_renaming_strategy.png
    :align: center
