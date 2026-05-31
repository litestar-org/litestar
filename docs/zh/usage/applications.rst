应用程序
=============

应用对象
-------------------

每个 Litestar 应用程序的核心是 :class:`~litestar.app.Litestar` 类的实例。通常，这段代码会放在项目根目录下名为 ``main.py``、``app.py``、``asgi.py`` 或类似的文件中。

这些入口点也会在 :ref:`CLI 自动发现 <usage/cli:autodiscovery>` 期间使用。

创建应用程序很简单 - 唯一必需的 :term:`参数 <argument>` 是一个包含 :class:`控制器 <.controller.Controller>`、:class:`路由器 <.router.Router>` 或 :class:`路由处理器 <.handlers.BaseRouteHandler>` 的 :class:`列表 <list>`：

.. literalinclude:: /examples/hello_world.py
    :language: python
    :caption: 一个简单的 Hello World Litestar 应用

应用实例是应用的根级别 - 它的基础路径为 ``/``，所有根级别的 :class:`控制器 <.controller.Controller>`、:class:`路由器 <.router.Router>` 和 :class:`路由处理器 <.handlers.BaseRouteHandler>` 都应该在其上注册。

.. seealso:: 要了解更多关于注册路由的信息，请查看文档中的这一章节：

    * :ref:`路由 - 注册路由 <usage/routing/overview:Registering Routes>`

启动和关闭
--------------------

您可以向 :class:`应用实例 <litestar.app.Litestar>` 的 :paramref:`~litestar.app.Litestar.on_startup` / :paramref:`~litestar.app.Litestar.on_shutdown` :term:`关键字参数 <argument>` 传递一个 :term:`可调用对象 <python:callable>` 列表 - 可以是同步或异步函数、方法或类实例。这些会在 ASGI 服务器（如 `uvicorn <https://www.uvicorn.org/>`_、`Hypercorn <https://hypercorn.readthedocs.io/en/latest/#/>`_、`Granian <https://github.com/emmett-framework/granian/>`_、`Daphne <https://github.com/django/daphne/>`_ 等）发出相应事件时按顺序调用。

.. mermaid::

   flowchart LR
       Startup[ASGI-事件: lifespan.startup] --> on_startup
       Shutdown[ASGI-事件: lifespan.shutdown] --> on_shutdown

这方面的经典用例是数据库连接。通常，我们希望在应用启动时建立数据库连接，然后在关闭时优雅地关闭它。

例如，让我们使用 `SQLAlchemy <https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html>`_ 的异步引擎创建数据库连接。我们创建两个函数，一个用于获取或建立连接，另一个用于关闭它，然后将它们传递给 :class:`~litestar.app.Litestar` 构造函数：

.. literalinclude:: /examples/startup_and_shutdown.py
    :language: python
    :caption: 启动和关闭

.. _lifespan-context-managers:

生命周期上下文管理器
-------------------------

除了生命周期钩子之外，Litestar 还支持使用 :term:`异步上下文管理器` 管理应用程序的生命周期。这在处理长时间运行的任务或需要保留某个上下文对象（如连接）时非常有用。

.. literalinclude:: /examples/application_hooks/lifespan_manager.py
    :language: python
    :caption: 处理数据库连接

执行顺序
------------------

当指定多个生命周期上下文管理器和 :paramref:`~litestar.app.Litestar.on_shutdown` 钩子时，Litestar 将在调用关闭钩子之前以相反的顺序调用 :term:`上下文管理器 <asynchronous context manager>`。

考虑这样一种情况，有两个生命周期上下文管理器 ``ctx_a`` 和 ``ctx_b`` 以及两个关闭钩子 ``hook_a`` 和 ``hook_b``，如以下代码所示：

.. code-block:: python
    :caption: 多个 :term:`上下文管理器 <asynchronous context manager>` 和关闭钩子的示例

    app = Litestar(lifespan=[ctx_a, ctx_b], on_shutdown=[hook_a, hook_b])

在关闭期间，它们按以下顺序执行：

.. mermaid::

    flowchart LR
        ctx_b --> ctx_a --> hook_a --> hook_b

如您所见，:term:`上下文管理器 <asynchronous context manager>` 以相反的顺序调用。另一方面，关闭钩子按照其指定的顺序调用。

.. _application-state:

使用应用程序状态
-----------------------

如 `on_startup / on_shutdown <#startup-and-shutdown>`_ 示例中所见，传递给这些钩子的 :term:`可调用对象 <python:callable>` 可以接收一个名为 ``app`` 的可选 :term:`关键字参数 <argument>`，通过它可以访问应用程序的状态对象和其他属性。使用应用程序 :paramref:`~.app.Litestar.state` 的优势在于它可以在连接的多个阶段访问，并且可以注入到依赖项和路由处理程序中。

应用程序状态是 :class:`.datastructures.state.State` 数据结构的实例，可以通过 :paramref:`~.app.Litestar.state` 属性访问。因此，它可以在应用实例可访问的任何地方访问。

:paramref:`~.app.Litestar.state` 是 :ref:`保留的关键字参数 <usage/routing/handlers:"reserved" keyword arguments>` 之一。

在此上下文中重要的是要理解，应用程序实例被注入到每个连接（即请求或 websocket 连接）的 ASGI ``scope`` 映射中，作为 ``scope["litestar_app"]``，并且可以使用 :meth:`~.Litestar.from_scope` 检索。这使得应用程序可以在 scope 映射可用的任何地方访问，例如在中间件、:class:`~.connection.request.Request` 和 :class:`~.connection.websocket.WebSocket` 实例上（作为 ``request.app`` / ``socket.app`` 访问）以及许多其他地方。

因此，:paramref:`~.app.Litestar.state` 提供了一种在应用程序的不同部分之间共享上下文数据的简单方法，如下所示：

.. literalinclude:: /examples/application_state/using_application_state.py
    :language: python
    :caption: 使用应用程序状态

.. _Initializing Application State:

初始化应用程序状态
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

要初始化应用程序状态，您可以将 :class:`~.datastructures.state.State` 对象传递给 Litestar 构造函数的 :paramref:`~.app.Litestar.state` 参数：

.. literalinclude:: /examples/application_state/passing_initial_state.py
    :language: python
    :caption: 使用应用程序状态

.. note:: :class:`~.datastructures.state.State` 可以使用 :class:`字典 <dict>`、:class:`~.datastructures.state.ImmutableState` 或 :class:`~.datastructures.state.State` 的实例，或包含键/值对的 :class:`元组 <tuple>` 的 :class:`列表` 进行初始化。

您可以指示 :class:`~.datastructures.state.State` 深度复制初始化数据，以防止从应用程序上下文外部进行修改。

为此，在 :class:`~.datastructures.state.State` 构造函数中将 :paramref:`~.datastructures.state.State.deep_copy` 设置为 ``True``。

将应用程序状态注入路由处理程序和依赖项
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

如上例所示，Litestar 提供了一种将状态注入路由处理程序和依赖项的简单方法 - 只需将 ``state`` 指定为处理程序或依赖函数的 kwarg。例如：

.. code-block:: python
    :caption: 在处理程序函数中访问应用程序 :class:`~.datastructures.state.State`

    from litestar import get
    from litestar.datastructures import State


    @get("/")
    def handler(state: State) -> None: ...

使用此模式时，您可以指定用于状态对象的类。此类型不仅用于类型检查器，Litestar 实际上会根据您在此处设置的类型实例化一个新的 ``state`` 实例。这允许用户使用自定义类作为 :class:`~.datastructures.state.State`。

虽然这非常强大，但它可能会鼓励用户遵循反模式：重要的是要强调，使用状态可能导致代码难以理解，并且由于不同 ASGI 上下文中的更改而导致难以理解的错误。因此，只有在这是最佳选择时才应使用此模式，并且应以有限的方式使用。为了不鼓励其使用，Litestar 还提供了内置的 :class:`~.datastructures.state.ImmutableState` 类。您可以使用此类来类型化状态并确保不允许对状态进行修改：

.. literalinclude:: /examples/application_state/using_immutable_state.py
    :language: python
    :caption: 使用自定义状态确保不可变性

应用程序钩子
-----------------

Litestar 包含几个应用程序级钩子，允许用户运行自己的同步或异步 :term:`可调用对象 <python:callable>`。虽然您可以根据需要使用这些钩子，但它们背后的设计意图是允许轻松地为可观察性（监控、跟踪、日志记录等）进行检测。

.. note:: 下面详述的所有应用程序钩子 kwargs 接收单个 :term:`python:callable` 或 :term:`可调用对象 <python:callable>` 的 :class:`列表`。如果提供 :class:`列表`，则按给定顺序调用。

异常发生后
^^^^^^^^^^^^^^^

:paramref:`~litestar.app.Litestar.after_exception` 钩子接受一个 :class:`同步或异步可调用对象 <litestar.types.AfterExceptionHookHandler>`，该可调用对象使用两个参数调用：发生的 ``exception`` 和请求或 websocket 连接的 ASGI ``scope``。

.. literalinclude:: /examples/application_hooks/after_exception_hook.py
    :language: python
    :caption: 异常后钩子

.. attention:: 此钩子不用于处理异常 - 它只是接收它们以允许副作用。要处理异常，您应该定义 :ref:`异常处理程序 <usage/exceptions:exception handling>`。

发送前
^^^^^^^^^^^

:paramref:`~litestar.app.Litestar.before_send` 钩子接受一个 :class:`同步或异步可调用对象 <litestar.types.BeforeMessageSendHookHandler>`，该可调用对象在发送 ASGI 消息时调用。该钩子接收消息实例和 ASGI ``scope``。

.. literalinclude:: /examples/application_hooks/before_send_hook.py
    :language: python
    :caption: 发送前钩子

初始化
^^^^^^^^^^^^^^

Litestar 包含一个钩子，用于拦截传递给 :class:`Litestar 构造函数 <litestar.app.Litestar>` 的参数，在它们用于实例化应用程序之前。

处理程序可以传递给应用程序构建时的 :paramref:`~.app.Litestar.on_app_init` 参数，并且每个处理程序将接收 :class:`~.config.app.AppConfig` 的实例，并且必须返回相同的实例。

此钩子对于在应用程序之间应用通用配置以及供希望开发第三方应用程序配置系统的开发人员使用非常有用。

.. note:: :paramref:`~.app.Litestar.on_app_init` 处理程序不能是 :ref:`python:async def` 函数，因为它们在 :paramref:`~litestar.app.Litestar.__init__` 中调用，在异步上下文之外。

.. literalinclude:: /examples/application_hooks/on_app_init.py
    :language: python
    :caption: 使用 ``on_app_init`` 钩子修改应用程序配置的示例。

.. _layered-architecture:

分层架构
--------------------

Litestar 有一个由 4 层组成的分层架构：

#. :class:`应用程序对象 <litestar.app.Litestar>`
#. :class:`路由器 <.router.Router>`
#. :class:`控制器 <.controller.Controller>`
#. :class:`处理程序 <.handlers.BaseRouteHandler>`

有许多 :term:`参数 <parameter>` 可以在每一层上定义，在这种情况下，在 **最接近处理程序** 的层上定义的 :term:`参数` 优先。这允许在配置复杂应用程序时实现最大的灵活性和简单性，并实现参数的透明覆盖。

支持分层的参数有：

* :ref:`after_request <after_request>`
* :ref:`after_response <after_response>`
* :ref:`before_request <before_request>`
* :ref:`cache_control <usage/responses:cache control>`
* :doc:`dependencies </usage/dependency-injection>`
* :doc:`dto </usage/dto/0-basic-use>`
* :ref:`etag <usage/responses:etag>`
* :doc:`exception_handlers </usage/exceptions>`
* :doc:`guards </usage/security/guards>`
* :ref:`include_in_schema <usage/openapi/schema_generation:configuring schema generation on a route handler>`
* :doc:`middleware </usage/middleware/index>`
* :ref:`opt <handler_opts>`
* :ref:`request_class <usage/requests:custom request>`
* :ref:`response_class <usage/responses:custom responses>`
* :ref:`response_cookies <usage/responses:setting response cookies>`
* :ref:`response_headers <usage/responses:setting response headers>`
* :doc:`return_dto </usage/dto/0-basic-use>`
* ``security``
* ``tags``
* :doc:`type_decoders </usage/custom-types>`
* :doc:`type_encoders </usage/custom-types>`
* :ref:`websocket_class <usage/websockets:custom websocket>`
