应用程序基础
==================

第一步
------------

在我们开始构建 TODO 应用程序之前，让我们先了解基础知识。


安装 Litestar
++++++++++++++++

要安装 Litestar，运行 ``pip install 'litestar[standard]'``。这将安装 Litestar 以及 `uvicorn <https://www.uvicorn.org/>`_ - 一个用于提供应用程序服务的 Web 服务器。

.. note::
    您可以使用任何支持 ASGI 的 Web 服务器，但本教程将使用 - Litestar 也推荐 - Uvicorn。


Hello, world!
+++++++++++++

您可以实现的最基本的应用程序 - 也是一个经典的应用程序 - 当然是打印 ``"Hello, world!"`` 的应用程序：


.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :caption: ``app.py``


现在将此示例的内容保存在名为 ``app.py`` 的文件中，并在终端中输入 ``litestar run``。这将在您的计算机上本地提供应用程序服务。现在在浏览器中访问 http://127.0.0.1:8000/：

.. image:: images/hello_world.png


现在我们有了一个可以工作的应用程序，让我们更详细地检查一下我们是如何实现的。


路由处理器
---------------

路由处理器告诉您的 Litestar 应用程序在收到请求时该做什么。之所以这样命名，是因为它们通常处理单个 URL 路径（或*路由*），这是特定于您的应用程序的 URL 部分。在我们当前的示例中，我们唯一的路由处理器是 ``hello_world``，它使用 ``/`` 路径。

.. tip::
    例如，如果您的应用程序有一个用于处理 ``/home`` URL 路径请求的路由，您将创建一个路由处理器函数，当收到对该路径的请求时将调用该函数。

路由处理器的第一个参数是*路径*，在本例中已设置为 ``/``。这意味着当对应用程序的 ``/`` 路径发出请求时，将调用函数 ``hello_world``。处理器装饰器的名称 - ``get`` - 指的是您想要响应的 HTTP 方法。使用 ``get`` 告诉 Litestar 您只想在发出 ``GET`` 请求时使用此函数。


.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :emphasize-lines: 4
    :linenos:


.. note::

    此示例中使用的语法（``@get`` 表示法）称为装饰器。它是一个函数，将另一个函数作为其参数（在本例中为 ``hello_world``）并用装饰器函数的返回值替换它。
    如果没有装饰器，示例将如下所示：

    .. code-block:: python

        async def hello_world() -> str:
            return "Hello, world!"


        hello_world = get("/")(hello_world)

    有关装饰器的深入解释，您可以阅读这篇优秀的 Real Python 文章：`Python 装饰器入门 <https://realpython.com/primer-on-python-decorators/>`_


.. seealso::

    * :doc:`/usage/routing/handlers`


类型注解
----------------

类型注解在 Litestar 应用程序中起着重要作用。它们告诉 Litestar 您希望数据如何行为，以及您打算如何使用它。


.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :emphasize-lines: 5
    :linenos:


在此示例中，``hello_world`` 函数的返回注解为 ``-> str``。这意味着它将返回一个 :class:`字符串 <str>`，并让 Litestar 知道您想按原样发送返回值。

.. note::
    虽然类型注解默认情况下不会影响运行时行为，但 Litestar 将它们用于许多事情，例如验证传入的请求数据。

    如果您使用静态类型检查器 - 例如 `mypy <https://mypy.readthedocs.io/en/stable/>`_ 或 `pyright <https://microsoft.github.io/pyright/#/>`_ - 这还有一个额外的好处，即使您的应用程序易于检查且更加类型安全。



应用程序
------------

定义路由处理器后，需要将其注册到应用程序才能开始处理请求。应用程序是 :class:`Litestar <litestar.app.Litestar>` 类的实例。这是一切的入口点，可以通过将之前定义的路由处理器列表作为第一个参数传递来注册它们：

.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :emphasize-lines: 9
    :linenos:


.. seealso::

    * :doc:`/usage/applications`



运行应用程序
-----------------------

最后一步是实际运行应用程序。Litestar 不包含自己的 HTTP 服务器，而是使用 `ASGI 协议 <https://asgi.readthedocs.io>`_，这是一个 Python 对象可以使用的协议，以便与实际实现 HTTP 协议并为您处理它的应用程序服务器（如 `uvicorn <https://www.uvicorn.org/>`_）进行交互。

如果您使用 ``pip install 'litestar[standard]'`` 安装了 Litestar，这将包含 *uvicorn* 以及 Litestar CLI。CLI 提供了一个方便的 uvicorn 包装器，允许您轻松运行应用程序而无需太多配置。

当您运行 ``litestar run`` 时，它将识别 ``app.py`` 文件及其中的 ``Litestar`` 实例，而无需手动指定。

.. tip::
    您可以在"重新加载模式"下启动服务器，这将在您对文件进行更改时重新加载应用程序。为此，只需将 ``--reload`` 标志作为命令行参数传递：``litestar run --reload``。


.. seealso::

    * :doc:`/usage/cli`
