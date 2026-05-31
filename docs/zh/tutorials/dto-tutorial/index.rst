数据传输对象教程
=============================

.. admonition:: 本教程适合谁?
    :class: info

    本教程旨在让你熟悉 Litestar 数据传输对象(DTO)的基本概念。假设你已经熟悉 Litestar 和路由处理器等基本概念。如果不熟悉,建议先学习 `开发基本 TODO 应用程序 <../todo-app>`_ 教程。

在本教程中,我们将逐步介绍对简单数据结构建模的过程,并演示如何使用 Litestar 的 DTO 工厂来帮助我们构建灵活的应用程序。让我们开始吧!

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/initial_pattern.py
    :language: python
    :caption: ``app.py``

在此脚本中,我们定义了一个数据模型、一个路由处理器和一个应用程序实例。

我们的数据模型是一个名为 ``Person`` 的 Python :func:`数据类 <dataclasses.dataclass>`,它有三个属性:``name``、``age`` 和 ``email``。

用 :class:`@get() <litestar.handlers.get>` 装饰的名为 ``get_person`` 的函数是一个路由处理器,路径为 ``/person/{name:str}``,用于处理 `GET <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET>`_ 请求。在路径中,``{name:str}`` 表示一个名为 ``name`` 的字符串类型的路径参数。路由处理器从路径参数接收名称并返回一个 ``Person`` 对象。

最后,我们创建一个应用程序实例并向其注册路由处理器。

在 Litestar 中,这种模式"开箱即用" - 也就是说,从处理器返回 :func:`数据类 <dataclasses.dataclass>` 实例是原生支持的。Litestar 将获取该数据类实例,并将其转换为可以通过网络发送的 :class:`bytes`。

让我们运行它并亲自看看!

将上面的脚本保存为 ``app.py``,使用 ``litestar run`` 命令运行它,然后在浏览器中访问 `<http://localhost:8000/person/peter>`_。你应该看到以下内容:

.. image:: images/initial_pattern.png
    :align: center

然而,真实世界的应用程序很少如此简单。如果我们想要限制在创建用户后暴露的有关用户的信息怎么办?例如,我们可能想要从响应中隐藏用户的电子邮件地址。这就是数据传输对象的用武之地。

.. toctree::
    :hidden:

    01-simple-dto-exclude
    02-nested-exclude
    03-nested-collection-exclude
    04-max-nested-depth
    05-renaming-fields
    06-receiving-data
    07-read-only-fields
    08-dto-data
    09-updating
    10-layered-dto-declarations
