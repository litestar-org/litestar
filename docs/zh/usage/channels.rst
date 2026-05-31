.. currentmodule:: litestar.channels

通道
========

**通道（Channels）** 是一组相关功能，旨在促进事件流的路由，例如可用于向 WebSocket 客户端广播消息。

通道提供：

1. 独立的 :term:`broker` 后端，可选地处理进程间通信和按需数据持久化
2. 基于"通道"的 :term:`subscription` 管理
3. 订阅者对象作为个性化 :term:`event stream` 的抽象，提供后台工作器和托管订阅
4. 同步和异步数据发布
5. 按 :term:`channel` 基础的可选 :term:`history` 管理
6. :doc:`WebSocket </usage/websockets>` 集成，为应用程序生成 WebSocket 路由处理器，以处理 :term:`subscription` 和将传入事件发布到已连接的客户端


基本概念
--------------

使用通道涉及几个移动部件。为了更好地熟悉概念、术语和数据流，提供了以下术语表和流程图

术语表
++++++++

.. dropdown:: 点击切换术语表

    .. glossary::

        event
            发布到或从绑定到最初发布它的 :term:`channel` 的 :term:`backend` 接收的单个数据片段

        event stream
            :term:`事件 <event>` 流，由 :term:`Subscriber` 之前订阅的所有通道的事件组成

        subscriber
            :class:`Subscriber <.subscriber.Subscriber>`：包装 :term:`event stream` 并通过各种方法提供访问的对象

        backend
            :class:`ChannelsBackend <.backends.base.ChannelsBackend>`。此对象管理插件和 :term:`broker` 之间的通信，向其发布消息并从中接收消息。每个插件实例与恰好一个后端关联。

        broker
            负责接收和发布消息到所有已连接的 :term:`backends <backend>`；共享相同 broker 的所有后端将访问相同的消息，允许进程间通信。这通常由单独的实体处理，例如 `Redis <https://redis.io/>`_

        plugin
            :class:`~.plugin.ChannelsPlugin`，管理 :term:`subscribers <subscriber>` 的中心实例，从 :term:`backend` 读取消息，将它们放入适当的 :term:`event stream`，并将数据发布到后端

        channel
            命名的订阅者组，可以向其发布数据。订阅者可以订阅多个通道，通道可以有多个订阅者

        subscription
            :term:`subscriber` 和 :term:`channel` 之间的连接，允许订阅者从通道接收事件

        backpressure
            防止 :term:`subscriber` 的积压无限增长的机制，通过丢弃新消息或驱逐旧消息

        history
            由 :term:`backend` 存储并可推送到 :term:`subscriber` 的一组先前发布的 :term:`events <event>`

        fanout
            将消息发送到通道的所有订阅者的过程

        eviction
            :term:`backpressure` 策略，当积压已满时添加新消息时丢弃积压中最旧的消息

        backoff
            :term:`backpressure` 策略，只要积压已满就丢弃新传入的消息

流程图
++++++++++

.. dropdown:: 点击切换流程图

    .. mermaid::
        :align: center
        :caption: 从应用程序到 :term:`broker` 的发布流

        flowchart LR
            Backend(Backend) --> Broker[(Broker)]

            Plugin{{Plugin}} --> Backend

            Application[[Application]] --> Plugin

    .. mermaid::
        :align: center
        :caption: 从 :term:`broker` 到套接字的数据扇出流，显示多个插件实例

        flowchart TD
            Broker[(Broker)]

            Broker --> Backend_1(Backend)
            Broker --> Backend_2(Backend)

            Backend_1 --> Plugin_1{{Plugin}}
            Backend_2 --> Plugin_2{{Plugin}}

            Plugin_1 --> Subscriber_1[Subscriber]
            Plugin_1 --> Subscriber_2[Subscriber]
            Plugin_1 --> Subscriber_3[Subscriber]

            Plugin_2 --> Subscriber_4[Subscriber]
            Plugin_2 --> Subscriber_5[Subscriber]
            Plugin_2 --> Subscriber_6[Subscriber]

:class:`ChannelsPlugin`
---------------------------

.. currentmodule:: litestar.channels.plugin

:class:`ChannelsPlugin` 充当管理通道和订阅者的中心实体。它用于发布消息、控制数据存储方式以及管理 :term:`subscribers <subscriber>`、路由处理器和配置。

.. tip:: 插件在 :paramref:`~ChannelsPlugin.channels` 键下作为依赖项提供自己，这意味着不需要导入它，而是可以直接从依赖树中的路由处理器或其他可调用对象中使用它

配置 :term:`channels <channel>`
++++++++++++++++++++++++++++++++++++++++++

插件管理的 :term:`channels <channel>` 可以预先定义，将它们传递给 :paramref:`~ChannelsPlugin.channels` 参数，或通过将 :paramref:`~ChannelsPlugin.arbitrary_channels_allowed` 设置为 ``True`` "即时"创建（即在第一次 :term:`subscription` 到通道时）。

.. code-block:: python
    :caption: 显式传递通道

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., channels=["foo", "bar"])

.. code-block:: python
    :caption: 允许任意通道

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., arbitrary_channels_allowed=True)

如果 :paramref:`~ChannelsPlugin.arbitrary_channels_allowed` 不是 ``True``，尝试发布或订阅未传递给 :paramref:`~ChannelsPlugin.channels` 的 :term:`channel` 将引发 :exc:`ChannelsException`。

发布数据
+++++++++++++++

插件的核心方面之一是发布数据，这通过其 :meth:`~ChannelsPlugin.publish` 方法完成：

.. code-block:: python
    :caption: 使用 :meth:`~ChannelsPlugin.publish` 将数据发布到通道

    channels.publish({"message": "Hello"}, "general")

上面的示例将数据发布到通道 ``general``，随后将其放入所有订阅者的 :term:`event stream` 中以供消费。

此方法是非阻塞的，即使通道和关联的 :term:`backends <backend>` 从根本上是异步的。

调用 :meth:`~ChannelsPlugin.publish` 有效地将消息排队以发送到后端，因此无法保证事件在此调用后立即在后端中可用。

或者，可以使用异步 :meth:`~ChannelsPlugin.wait_published` 方法，它跳过内部消息队列，直接将数据发布到后端。

.. note::
    虽然调用 :meth:`~ChannelsPlugin.publish` 不保证消息立即发送到后端，但它将 *最终* 发送到那里；在关闭时，插件将等待所有队列清空

管理 :term:`subscriptions <subscription>`
++++++++++++++++++++++++++++++++++++++++++++++++

插件的另一个核心功能是管理 :term:`subscriptions <subscription>`，为此存在两种不同的方法：

1. 通过 :meth:`~ChannelsPlugin.subscribe` 和 :meth:`~ChannelsPlugin.unsubscribe` 方法手动管理
2. 通过使用 :meth:`~ChannelsPlugin.start_subscription` 上下文管理器

:meth:`~ChannelsPlugin.subscribe` 和 :meth:`~ChannelsPlugin.start_subscription` 都产生一个 :class:`Subscriber`，可用于与订阅的事件流交互。

应该首选上下文管理器，因为它确保通道被取消订阅。仅在无法使用 :term:`context manager <asynchronous context manager>` 时才应使用 :meth:`~ChannelsPlugin.subscribe` 和 :meth:`~ChannelsPlugin.unsubscribe` 方法，例如当 :term:`subscription` 跨越不同上下文时。

.. code-block:: python
    :caption: 手动调用 :term:`subscription` 方法

    subscriber = await channels.subscribe(["foo", "bar"])
    try:
        ...  # 在这里做一些事情
    finally:
        await channels.unsubscribe(subscriber)

.. code-block:: python
    :caption: 使用 :term:`async context manager <asynchronous context manager>`

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # 在这里做一些事情

也可以取消订阅单个 :term:`channels <channel>`，如果需要动态管理 :term:`subscriptions <subscription>`，这可能是理想的。

.. code-block:: python
    :caption: 手动取消订阅通道

    subscriber = await channels.subscribe(["foo", "bar"])
    try:
        ...  # 在这里做一些事情
    finally:
        await channels.unsubscribe(subscriber, ["foo"])


或者，使用上下文管理器

.. code-block:: python
    :caption: 使用 :term:`async context manager <asynchronous context manager>` 取消订阅 :term:`channel`

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # 在这里做一些事情
        await channels.unsubscribe(subscriber, ["foo"])

管理 :term:`history`
++++++++++++++++++++++++

一些后端支持按 :term:`channel` 的 :term:`history`，在存储中保留一定数量的 :term:`events <event>`。然后可以将此 :term:`history` 推送到 :term:`subscriber`。

插件的 :meth:`put_subscriber_history <ChannelsPlugin.put_subscriber_history>` 可用于获取此 :term:`history` 并将其放入订阅者的 :term:`event stream` 中。

.. literalinclude:: /examples/channels/put_history.py
    :caption: 检索 :term:`subscriber` 的 :term:`channel` :term:`history` 并将其放入 :term:`stream <event stream>` 中

.. note::
    :term:`history` 的发布是按顺序进行的，一次一个 :term:`channel` 和一个 :term:`event`。这样做是为了确保事件的正确排序并避免填满 :term:`subscriber` 的积压，这将导致丢弃 :term:`history` 条目。如果条目数量超过最大积压大小，执行将等待直到先前的事件已被处理。

   阅读更多：`管理反压`_

:class:`Subscriber`
-----------------------

.. py:currentmodule:: litestar.channels.subscriber

:class:`Subscriber` 管理由插件提供给它的单个 :term:`event stream`，表示订阅者已订阅的所有 :term:`channels <channel>` 的事件总和。

它可以被视为所有 :term:`events <event>` 的端点，而后端充当源，插件充当路由器，负责将从后端收集的事件提供到适当的订阅者流中。

除了是 :term:`event stream` 的抽象之外，:class:`Subscriber` 提供了两种处理此流的方法：

:meth:`iter_events <Subscriber.iter_events>`
    :term:`asynchronous generator`，一次从流中产生一个事件，等待直到下一个可用

:meth:`run_in_background <Subscriber.run_in_background>`
    :term:`context manager <asynchronous context manager>`，包装 :class:`asyncio.Task`，使用 :meth:`iter_events <Subscriber.iter_events>` 产生的事件，为每个事件调用提供的 :term:`callback`。退出时，它将尝试正常关闭正在运行的任务，等待流中当前排队的所有事件被处理。如果上下文以错误退出，任务将被取消。

    可以通过在 :meth:`run_in_background <Subscriber.run_in_background>` 中将 :paramref:`~Subscriber.run_in_background.join` 设置为 ``False`` 来强制任务立即停止，这将导致任务被取消。默认情况下，这仅在上下文以异常离开时发生。

.. important::
    :term:`event streams <event stream>` 中的 :term:`events <event>` 始终是字节；调用 :meth:`ChannelsPlugin.publish` 时，数据将在发送到后端之前被序列化。

消费 :term:`event stream`
++++++++++++++++++++++++++++++++++

消费 :term:`event stream` 有两种通用方法：

1. 使用 :meth:`iter_events <Subscriber.iter_events>` 直接迭代它
2. 使用 :meth:`run_in_background <Subscriber.run_in_background>` 上下文管理器，它启动后台任务，迭代流，为每个接收的 :term:`event` 调用提供的回调

直接迭代 :term:`stream <event stream>` 主要在处理事件是唯一关注点时有用，因为 :meth:`iter_events <Subscriber.iter_events>` 实际上是一个无限循环。对于所有其他应用程序，使用上下文管理器更可取，因为它允许轻松并发运行其他代码。

.. literalinclude:: /examples/channels/iter_stream.py
    :caption: 迭代 :term:`event stream` 以将数据发送到 WebSocket

在上面的示例中，流用于将数据发送到 :class:`WebSocket <litestar.connection.WebSocket>`。

通过将 :meth:`Websocket.send_text() <litestar.connection.WebSocket.send_text>` 作为回调传递给 :meth:`~Subscriber.run_in_background`，可以实现相同的效果。这将导致每次新 :term:`event` 在 :term:`stream <event stream>` 中可用时调用 WebSocket 的方法，但将控制权交还给应用程序，提供执行其他任务的机会，例如从套接字接收传入数据。

.. literalinclude:: /examples/channels/run_in_background.py
    :caption: 使用 :meth:`~Subscriber.run_in_background` 并发处理事件

.. important:: 与 WebSocket 一起使用时，应谨慎使用迭代 :meth:`~Subscriber.iter_events`。

    由于 :exc:`WebSocketDisconnect` 仅在相应的 ASGI 事件被 *接收* 后引发，它可能导致无限期挂起的协程。例如，如果客户端断开连接，但没有收到进一步的事件，就会发生这种情况。生成器将等待新事件，但由于它永远不会收到任何事件，因此不会在 WebSocket 上进行 ``send`` 调用，这反过来意味着不会引发异常来打破循环。

管理 :term:`backpressure`
-----------------------------

每个订阅者管理自己的积压：未处理的 :term:`events <event>` 队列。默认情况下，此积压的大小是无限的，允许它无限增长。对于大多数应用程序，这应该不是问题，但当接收者一致地无法比消息进入更快地处理消息时，应用程序可能选择处理这种情况。

通道插件为管理此 :term:`backpressure` 提供了两种不同的策略：

1. :term:`backoff` 策略，只要积压已满就丢弃新传入的消息
2. :term:`eviction` 策略，当积压已满时添加新消息时丢弃积压中最旧的消息

.. code-block:: python
    :caption: Backoff 策略

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        max_backlog=1000,
        backlog_strategy="backoff",
    )

.. code-block:: python
    :caption: :term:`Eviction <eviction>` 策略

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        max_backlog=1000,
        backlog_strategy="dropleft",
    )

后端
--------

消息的存储和 :term:`fanout` 由 :class:`ChannelsBackend <litestar.channels.backends.base.ChannelsBackend>` 处理。

当前实现了以下后端：

:class:`MemoryChannelsBacked <.memory.MemoryChannelsBackend>`
    基本的内存后端，主要用于测试和本地开发，但仍然完全有能力。由于它在进程内存储所有数据，因此可以实现所有后端中最高的性能，但同时不适合在多个进程上运行的应用程序。

:class:`RedisChannelsPubSubBackend <.redis.RedisChannelsPubSubBackend>`
    基于 Redis 的后端，使用 `Pub/Sub <https://redis.io/docs/manual/pubsub/>`_ 传递消息。此 Redis 后端具有低延迟和开销，如果不需要 :term:`history`，通常推荐使用

:class:`RedisChannelsStreamBackend <.redis.RedisChannelsStreamBackend>`
    基于 redis 的后端，使用 `streams <https://redis.io/docs/data-types/streams/>`_ 传递消息。与 Pub/Sub 后端相比，发布时的延迟略高，但在消息 :term:`fanout` 中实现相同的吞吐量。当需要 :term:`history` 时推荐使用

:class:`AsyncPgChannelsBackend <.asyncpg.AsyncPgChannelsBackend>`
    使用 `asyncpg <https://magicstack.github.io/asyncpg/current/>`_ 驱动程序的 postgres 后端

:class:`PsycoPgChannelsBackend <.psycopg.PsycoPgChannelsBackend>`
    使用 `psycopg3 <https://www.psycopg.org/psycopg3/docs/>`_ 异步驱动程序的 postgres 后端

与 websocket 处理器集成
-----------------------------------

生成路由处理器
++++++++++++++++++++++

一个常见的模式是为每个 :term:`channel` 创建一个路由处理器，从该通道向已连接的客户端发送数据。这可以完全自动化，使用插件创建这些路由处理器。

.. literalinclude:: /examples/channels/create_route_handlers.py
    :language: python
    :caption: 设置 ``create_ws_route_handlers=True`` 将为所有 ``channels`` 创建路由处理器

生成的路由处理器可以选择配置为在客户端连接后发送 :term:`channel` 的 :term:`history`：

.. literalinclude:: /examples/channels/create_route_handlers_send_history.py
    :caption: 客户端连接后发送前 10 个 :term:`history` 条目

.. tip:: 在 :class:`ChannelsPlugin` 上使用 :paramref:`~litestar.channels.plugin.ChannelsPlugin.arbitrary_channels_allowed` 参数时，将生成单个路由处理器，使用 :ref:`路径参数 <usage/routing/parameters:path parameters>` 指定通道名称
