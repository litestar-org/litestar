回顾和组装最终应用程序
===========================================

到目前为止,我们已经独立地查看了应用程序的不同部分,但现在是时候将它们全部组合起来并组装一个完整的应用程序了。


最终应用程序
-----------------

.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :linenos:


回顾
-----


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 28-32
    :lineno-start: 28


用 ``get("/")`` 设置的路由处理器响应 ``GET`` 请求并返回我们 TODO 列表上的所有项目的列表。
可选的查询参数 ``done`` 允许按状态过滤项目。``bool`` 的类型注解将查询参数转换为
:class:`bool`,并将其包装在 :class:`Optional <typing.Optional>` 中使其成为可选的。


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 35-38
    :lineno-start: 35


用 ``post("/")`` 设置的路由处理器响应 ``POST`` 请求并向 TODO 列表添加一个项目。新项目的数据通过请求数据接收,路由处理器通过指定 ``data`` 参数来访问它。``TodoItem`` 的类型注解意味着请求数据将被解析为 JSON,然后用于创建 ``TodoItem`` 数据类的实例,该实例最终被传递到函数中。



.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 41-46
    :lineno-start: 41


用 ``put("/{item_title:str}")`` 设置的路由处理器利用路径参数,响应路径 ``/some todo title`` 上的 ``PUT`` 请求,其中 ``some todo title`` 是你希望更新的 ``TodoItem`` 的标题。它通过同名的函数参数 ``item_title`` 接收路径参数的值。路径参数中的 ``:str`` 后缀意味着它将被视为字符串。此外,这个路由处理器以与 ``POST`` 处理器相同的方式接收 ``TodoItem`` 的数据。


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 49
    :lineno-start: 49


创建了一个 ``Litestar`` 实例,包括之前定义的路由处理器。
现在可以使用像 `uvicorn <https://www.uvicorn.org/>`_ 这样的 ASGI 服务器来提供此应用,这可以通过执行 ``litestar run`` 命令使用 Litestar 的 CLI 方便地完成。


下一步
----------

本教程介绍了 Litestar 的一些基本概念。有关这些主题的更深入解释,请参阅 :doc:`使用指南 </usage/index>`。
