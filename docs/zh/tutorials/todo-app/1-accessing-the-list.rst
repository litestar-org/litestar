访问列表
====================

简介
-----

您要为应用程序设置的第一件事是返回单个 TODO 列表的路由处理器。在这种情况下，TODO 列表将是表示该 TODO 列表上项目的字典列表。

.. literalinclude:: /examples/todo_app/get_list/dict.py
    :language: python
    :caption: ``app.py``
    :linenos:


如果您运行应用程序并在浏览器中访问 http://127.0.0.1:8000/，您将看到以下输出：

.. figure:: images/get_todo_list.png

    突然，JSON


因为 ``get_list`` 函数已用 ``List[Dict[str, Union[str, bool]]]`` 注解，Litestar 推断您希望从中返回的数据被序列化为 JSON：

.. literalinclude:: /examples/todo_app/get_list/dict.py
    :language: python
    :lineno-start: 13
    :lines: 13


使用数据类清理示例
++++++++++++++++++++++++++++++++++++++++

为了让您的生活更轻松一点，您可以通过使用 :py:mod:`dataclasses` 而不是普通字典来转换此示例：

.. tip:: 有关数据类的深入解释，您可以阅读这篇优秀的 Real Python 文章：`Python 3.7+ 中的数据类 <https://realpython.com/python-data-classes/>`_

.. literalinclude:: /examples/todo_app/get_list/dataclass.py
    :caption: ``app.py``
    :language: python
    :linenos:


这看起来干净多了，并且具有能够使用数据类而不是普通字典的附加好处。结果仍然相同：Litestar 知道如何将这些数据类转换为 JSON，并将自动为您执行此操作。

.. tip::
    除了数据类，Litestar 还支持更多类型，例如 :class:`TypedDict <typing.TypedDict>`、:class:`NamedTuple <typing.NamedTuple>`、
    `Pydantic 模型 <https://docs.pydantic.dev/usage/models/>`_ 或 `attrs 类 <https://www.attrs.org/en/stable/>`_。


使用查询参数过滤列表
-----------------------------------------

目前 ``get_list`` 将始终返回列表上的所有项目，但如果您只对具有特定状态的项目感兴趣，例如所有尚未标记为*已完成*的项目，该怎么办？

为此，您可以使用查询参数；要定义查询参数，只需向函数添加一个未使用的参数即可。Litestar 将识别这一点并推断它将用作查询参数。发出请求时，查询参数将从 URL 中提取，并传递给同名的函数参数。

.. literalinclude:: /examples/todo_app/get_list/query_param.py
    :caption: ``app.py``
    :language: python
    :linenos:


.. figure:: images/todos-done.png

    访问 http://127.0.0.1:8000?done=1 将为您提供所有已标记为*已完成*的 TODO


.. figure:: images/todos-not-done.png

    而 http://127.0.0.1:8000?done=0 将仅返回那些尚未完成的


乍一看这似乎工作得很好，但您可能会发现一个问题：如果您输入除 ``?done=1`` 之外的任何内容，它仍然会返回尚未标记为完成的项目。例如，``?done=john`` 给出的结果与 ``?done=0`` 相同。

一个简单的解决方案是简单地检查查询参数是 ``1`` 还是 ``0``，如果是其他内容，则返回带有指示错误的 HTTP 状态码的响应：

.. literalinclude:: /examples/todo_app/get_list/query_param_validate_manually.py
    :caption: ``app.py``
    :language: python
    :linenos:

如果查询参数等于 ``1``，返回所有 ``done=True`` 的项目：

.. literalinclude:: /examples/todo_app/get_list/query_param_validate_manually.py
    :language: python
    :caption: ``app.py``
    :lines: 23-24
    :dedent: 2
    :linenos:
    :lineno-start: 23


如果查询参数等于 ``0``，返回所有 ``done=False`` 的项目：

.. literalinclude:: /examples/todo_app/get_list/query_param_validate_manually.py
    :language: python
    :caption: ``app.py``
    :lines: 25-26
    :dedent: 2
    :linenos:
    :lineno-start: 25

最后，如果查询参数具有任何其他值，将引发 :exc:`HTTPException`。引发 ``HTTPException`` 告诉 Litestar 出了问题，它不会返回正常响应，而是发送一个带有给定 HTTP 状态码（在本例中为 ``400``）和提供的错误消息的响应。

.. literalinclude:: /examples/todo_app/get_list/query_param_validate_manually.py
    :language: python
    :caption: ``app.py``
    :lines: 27
    :dedent: 2
    :linenos:
    :lineno-start: 27


.. figure:: images/done-john.png

    现在尝试访问 http://127.0.0.1:8000?done=john，您将收到此错误消息


现在我们已经解决了这个问题，但您的代码对于如此简单的任务而言变得相当复杂。您可能在想`"一定有更好的方法！" <https://www.youtube.com/watch?t=566&v=p33CVV29OG8>`_，确实有！您不必手动执行这些操作，只需让 Litestar 为您处理即可！


转换和验证查询参数
+++++++++++++++++++++++++++++++++++++++

如前所述，类型注解在 Litestar 中不仅可用于静态类型检查；它们还可以定义和配置行为。在这种情况下，您可以让 Litestar 将查询参数转换为布尔值，匹配 ``TodoItem.done`` 属性的值，并在同一步骤中验证它，如果提供的值不是有效的布尔值，则为您返回错误响应。

.. literalinclude:: /examples/todo_app/get_list/query_param_validate.py
    :language: python
    :caption: ``app.py``
    :linenos:


.. figure:: images/done-john-2.png

    浏览到我们之前示例中的 http://127.0.0.1:8000?done=john，您将看到它现在会产生这个描述性的错误消息


**这里发生了什么？**

由于 :class:`bool` 被用作 ``done`` 参数的类型注解，Litestar 将首先尝试将值转换为 :class:`bool`。由于 ``john``（可以说）不是布尔值的表示，它将返回一个错误响应。

.. literalinclude:: /examples/todo_app/get_list/query_param_validate.py
    :language: python
    :caption: ``app.py``
    :lines: 21
    :linenos:
    :lineno-start: 21

.. tip::
    需要注意的是，此转换不是在原始值上调用 :class:`bool` 的结果。``bool("john")`` 将是 :obj:`True`，因为 Python 将所有非空字符串视为真值。

    然而，Litestar 支持 HTTP 世界中常用的习惯布尔表示；``true`` 和 ``1`` 都转换为 :obj:`True`，而 ``false`` 和 ``0`` 转换为 :obj:`False`。


但是，如果转换成功，``done`` 现在是一个 :class:`bool`，然后可以与 ``TodoItem.done`` 属性进行比较：

.. literalinclude:: /examples/todo_app/get_list/query_param_validate.py
    :language: python
    :caption: ``app.py``
    :lines: 22
    :dedent: 2
    :linenos:
    :lineno-start: 22


.. seealso::

    * :ref:`路由 - 参数 - 类型强制转换 <usage/routing/parameters:type coercion>`


使查询参数可选
+++++++++++++++++++++++++++++++++++

还有一个问题需要解决，那就是，当您想要获取**所有**项目（无论是否完成）并省略查询参数时会发生什么？

.. figure:: images/missing-query.png

    省略 ``?done`` 查询参数将导致错误

因为查询参数已定义为 ``done: bool`` 而没有给它一个默认值，它将被视为必需参数 - 就像常规函数参数一样。如果您希望这是可选的，则需要提供默认值。

.. literalinclude:: /examples/todo_app/get_list/query_param_default.py
    :language: python
    :caption: ``app.py``
    :linenos:


.. figure:: images/get_todo_list.png

    再次浏览到 http://localhost:8000，您将看到如果省略查询参数，它不会返回错误


.. tip::
    在这种情况下，默认值已设置为 :obj:`None`，因为如果未指定 ``done`` 状态，我们不想进行任何过滤。如果您希望默认仅显示未完成的项目，可以将值设置为 :obj:`False`。


.. seealso::

    * :ref:`路由 - 参数 - 查询参数 <usage/routing/parameters:query parameters>`


交互式文档
--------------------------

到目前为止，我们已经通过手动导航来探索 TODO 应用程序，但还有另一种方法：Litestar 配备了交互式 API 文档，它会自动为您生成。您只需运行应用程序（``litestar run``）并访问 http://127.0.0.1:8000/schema/swagger

.. figure:: images/swagger-get.png

    之前设置的路由处理器将显示在交互式文档中


此文档不仅概述了您构建的 API，还允许您向其发送请求。

.. figure:: images/swagger-get-example-request.png

    执行我们之前执行的相同请求


.. note::
    这是通过 `Swagger <https://swagger.io/>`_ 和 `OpenAPI <https://www.openapis.org/>`_ 实现的。Litestar 根据路由处理器生成 OpenAPI 模式，然后 Swagger 可以使用该模式来设置交互式文档。

.. tip::
    除了 Swagger，Litestar 还使用 `ReDoc <https://redocly.com/>`_ 和 `Stoplight Elements <https://stoplight.io/open-source/elements/>`_ 从生成的 OpenAPI 模式提供文档。您可以分别浏览到 http://127.0.0.1:8000/schema/redoc 和 http://127.0.0.1:8000/schema/elements 进行查看。
