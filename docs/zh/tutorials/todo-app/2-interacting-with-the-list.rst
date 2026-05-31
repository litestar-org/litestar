让列表可交互
============================

到目前为止,我们的 TODO 列表应用程序还不是很有用,因为它是静态的。你不能更新项目,也不能添加或删除它们。

接收传入数据
-----------------------

让我们首先实现一个处理创建新项目的路由处理器。
在上一步中,你使用了 ``get`` 装饰器,它响应 ``GET`` HTTP 方法。在这种情况下,我们想要对 ``POST`` 请求做出反应,因此我们将使用相应的 ``post`` 装饰器。

.. literalinclude:: /examples/todo_app/create/dict.py
    :language: python
    :linenos:

可以通过 ``data`` 关键字接收请求数据。Litestar 会识别这一点,并通过此参数提供随请求发送的数据。与上一章中的查询参数一样,我们使用类型注解来配置我们期望接收的数据类型,并设置验证。在这种情况下,Litestar 将期望 JSON 格式的请求数据,并使用我们给出的类型注解将其转换为正确的格式。

.. seealso::

    * :doc:`/usage/requests`


使用交互式文档测试路由
++++++++++++++++++++++++++++++++++++++++++++++++++++

由于我们的示例现在使用 ``POST`` HTTP 方法,你不能再简单地在浏览器中访问 URL 并获得响应。相反,你可以使用交互式文档发送 ``POST`` 请求。由于 Litestar 生成的 OpenAPI 架构,Swagger 会确切地知道要发送什么样的数据。在这个示例中,它将发送一个简单的 JSON 对象。

.. figure:: images/swagger-post-dict-response.png

    向我们的 ``add_item`` 路由发送示例请求会显示成功的响应


使用数据类改进示例
++++++++++++++++++++++++++++++++++++++

与上一章一样,这也可以通过使用 :doc:`数据类 <python:library/dataclasses>` 而不是普通的字典来改进。

.. literalinclude:: /examples/todo_app/create/dataclass.py
    :language: python
    :linenos:


这不仅看起来更清晰,并为代码添加了更多结构,而且还提供了更好的交互式文档;现在它将向我们展示我们定义的数据类的字段名称和默认值:

.. figure:: images/swagger-dict-vs-dataclass.png

    ``add_item`` 路由的文档,其中 ``data`` 类型为 ``dict`` vs ``dataclass``

使用数据类还能提供更好的验证:省略像 ``title`` 这样的键将导致有用的错误响应:


.. figure:: images/swagger-dataclass-bad-body.png

    发送没有 ``title`` 键的请求会失败


使用路径参数创建动态路由
-------------------------------------------

列表上的下一个任务是更新项目的状态。为此,需要一种方法来引用列表上的特定项目。这可以使用查询参数来完成,但有一种更简单、语义上更连贯的方式来表达这一点:路径参数。

.. code-block:: python

    @get("/{name:str}")
    async def greeter(name: str) -> str:
        return "Hello, " + name


到目前为止,你的应用程序中的所有路径都是静态的,这意味着它们由不会改变的常量字符串表示。实际上,到目前为止使用的唯一路径是 ``/``。

路径参数允许你构建动态路径,并稍后引用动态捕获的部分。这听起来一开始可能很复杂,但实际上非常简单;你可以将其视为在请求的路径上使用的正则表达式。

路径参数由两部分组成:路径内部描述参数的表达式,以及路由处理器函数中同名的相应函数参数,它将接收路径参数的值。

在上面的示例中,声明了一个路径参数 ``name:str``,这意味着现在可以向路径 ``/john`` 发出请求,并且 ``greeter`` 函数将被调用为 ``greeter(name="john")``,类似于查询参数的注入方式。


.. tip::
    就像查询参数一样,路径参数也可以转换和验证它们的值。这是使用 ``:type`` 冒号注解配置的,类似于类型注解。例如,``value:str`` 将以字符串形式接收值,而 ``value:int`` 将尝试将其转换为整数。

    支持的类型的完整列表可以在这里找到:
    :ref:`usage/routing/parameters:支持的路径参数类型`


通过使用这种模式并将其与前面部分关于接收数据的模式结合起来,你现在可以设置一个路由处理器,它接收 TODO 项目的标题、以数据类实例形式的更新项目,并更新列表中的项目。


.. literalinclude:: /examples/todo_app/update.py
    :language: python


.. seealso::

    * :ref:`usage/routing/parameters:路径参数`
