.. currentmodule:: litestar.channels

WebSocket Channels
===================

**Channels** are a group of related functionalities facilitating the broadcasting of
data through WebSockets. In particular, they offer:

1. Data publishing through different channels, optionally managing inter-process communication
2. Channel based subscription management
3. Sending of published data through, and lifetime management of :class:`WebSocket <.connection.WebSocket>` connections
4. Automated management of "channel rooms"; WebSocket route handler endpoints, which accept a connection, subscribe
   to a channel and send broadcast messages to the connected socket
5. "Channel history": Store and publish a certain amount of messages and send them to new subscribers


.. code-block:: python

    from litestar import Litestar
    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        arbitrary_channels_allowed=True,
        create_route_handlers=True,
        handler_base_path="/ws",
    )

    app = Litestar([], plugins=[channels])


This is all that's required to set up a basic application using channels. Out of the box
this application will now:

1. Accept WebSocket connections on all paths following the ``/ws/<channel name>`` pattern
2. Subscribe newly connected sockets to respective channel given by the path parameter
3. Send all published events on that channel to all connected sockets
4. Allow publishing events using
   :meth:`channels.publish() <litestar.channels.plugin.ChannelsPlugin.publish>`


Basic concepts
--------------

Utilizing channels involves a few moving parts, of which the most important ones are:

1. The :class:`ChannelsPlugin <.plugin.ChannelsPlugin>`, a central instance managing
   subscribers, the backend, root event stream, route handlers and general configuration
2. A :class:`ChannelsBackend <.base.ChannelsBackend>`, responsible for synchronizing and
   publishing events
3. :class:`Subscriber <.plugin.Subscriber>`, an entity representing an individualized
   event stream, receiving events from all channels this subscriber is subscribed to


Flowcharts
++++++++++


.. mermaid::
    :align: center
    :caption: Publishing flow from the application to the broker

    flowchart LR
        Backend(Backend) --> Broker[(Broker)]

        Plugin{{Plugin}} --> Backend

        Application[[Application]] --> Plugin


.. mermaid::
    :align: center
    :caption: Fanout flow of data from the broker to the sockets, showing multiple plugin instances

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

        Subscriber_1 --> Socket_1((Socket))
        Subscriber_2 --> Socket_2((Socket))
        Subscriber_3 --> Socket_3((Socket))

        Subscriber_4 --> Socket_4((Socket))
        Subscriber_5 --> Socket_5((Socket))
        Subscriber_6 --> Socket_6((Socket))



The ``ChannelsPlugin``
----------------------

.. currentmodule:: litestar.channels.plugin

The :class:`ChannelsPlugin` acts as the central entity for managing channels and
subscribers. It's used to publish messages, controls how data is stored, manages
subscribers, route handlers and configuration.


.. tip::
    The plugin makes itself available as a dependency under the ``channels`` key, which
    means it's not needed to import it and instead, it can be used from within route
    handlers or other callables within the dependency tree directly.


Configuring the channels
+++++++++++++++++++++++++

The channels manged by the plugin can be either defined upfront, passing them to the
``channels`` argument, or be created "on the fly" (i.e. on the first subscription to a
channel) by setting ``arbitrary_channels_allowed=True``.


.. code-block:: python
    :caption: Passing channels explicitly

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., channels=["foo", "bar"])


.. code-block:: python
    :caption: Allowing arbitrary channels

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., arbitrary_channels_allowed=True)


If ``arbitrary_channels_allowed`` is not ``True``, trying to publish or subscribe to a
channel not passed to ``channels`` will raise a :exc:`ChannelsException`.


Publishing data
+++++++++++++++


One of the core aspects of the plugin is publishing data, which is done through its
:meth:`publish <ChannelsPlugin.publish>` method:

.. code-block:: python

    channels.publish({"message": "Hello"}, "general")


The above example will publish the data to the channel ``general``, subsequently putting
it into all subscriber's respective event streams to be consumed.

.. important::
    While WebSockets and the channels plugin are fundamentally asynchronous, the
    :meth:`publish <ChannelsPlugin.publish>` is synchronous. It is however non-blocking;
    The messages are buffered internally and published to the backend in an
    asynchronous manner.

    The reason for this is to provide an easy way to publish data from synchronous
    context.


Managing subscriptions
++++++++++++++++++++++

Another core functionality of the plugin is managing subscriptions, for which two
different approaches exist:

1. Manually through the :meth:`subscribe <ChannelsPlugin.subscribe>` and
   :meth:`unsubscribe <ChannelsPlugin.unsubscribe>` methods
2. By using the :meth:`start_subscription <ChannelsPlugin.start_subscription>` context
   manager

Both :meth:`subscribe <ChannelsPlugin.subscribe>` and
:meth:`start_subscription <ChannelsPlugin.start_subscription>` produce a
:class:`Subscriber`, which can be used to interact with the streams of events subscribed
to.

The context manager should be preferred, and using the methods directly should only be
done when a context manager cannot be used, e.g. when the subscription would span
different contexts.


.. code-block:: python
    :caption: Calling the subscription methods manually

    subscriber = await channels.subscribe(["foo", "bar"])
    try:
        ...  # do some stuff here
    finally:
        await channels.unsubscribe(subscriber)



.. code-block:: python
    :caption: Using the context manager

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # do some stuff here


It is also possible to unsubscribe from individual channels, which may be desirable if
subscriptions need to be managed dynamically.

.. code-block:: python

    subscriber = await channels.subscribe(["foo", "bar"])
    ...  # do some stuff here
    await channels.unsubscribe(subscriber, ["foo"])


Or, using the context manager

.. code-block:: python

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # do some stuff here
        await channels.unsubscribe(subscriber, ["foo"])



The ``Subscriber``
------------------

The :class:`Subscriber` manages an individual event stream, provided to it by the
plugin, consisting representing the sum of events from all channels the subscriber has
subscribed to.

It can be considered the endpoint of all events, while the backends act as the source,
and the plugin as a router, being responsible for supplying events gathered from the
backend into the appropriate subscriber's streams.

In addition to being an abstraction of customized event stream, the :class:`Subscriber`
provides different methods to handle this stream:

:meth:`iter_events <Subscriber.iter_events>`
    An asynchronous generator, producing one event from the stream at a time, blocking
    until the next one becomes available

:meth:`start_in_background <.Subscriber.start_in_background>`
    Starts a :class:`asyncio.Task` which runs in the background, consuming the event
    stream and sending received events to a provided
    :class:`WebSocket <litestar.connection.WebSocket>`

:meth:`run_in_background <.Subscriber.run_in_background>`
    A context manager, wrapping
    :meth:`start_in_background <.Subscriber.start_in_background>`. Upon exit, it will
    attempt a graceful shutdown of the running task, waiting for all currently enqueued
    events in the stream to be processed. Should the context be left with an error, the
    task will be cancelled instead.

    This should be the preferred method of running the background task, since it ensures
    the task's lifetime is handled correctly

    .. tip::
        It's possible to force the task to stop immediately, by passing ``join=False`` to
        :meth:`run_in_background <.plugin.Subscriber.run_in_background>`, which will lead
        to the cancellation of the task. By default this only happens when the context is
        left with an exception.

:meth:`put_history <.Subscriber.put_history>`
    Retrieve the history for a given channel and put it into the subscriber's event
    stream


.. important::
    The events in the event streams are always bytes; When calling
    :meth:`ChannelsPlugin.publish`, data will be serialized before being sent to the
    backend.


Integrating with websocket handlers
-----------------------------------

Using the methods described above, it's possible to integrate all functionality within a
regular :class:`websocket route handler <litestar.handlers.websocket>`.


Consuming the event stream directly
+++++++++++++++++++++++++++++++++++

If an application needs more fine grained control over how data is being sent, a
:class:`Subscriber <.plugin.Subscriber>`\ 's event stream can be consumed directly,
using :meth:`iter_events <.plugin.Subscriber.iter_events>`:


.. code-block:: python

    from litestar import websocket, WebSocket
    from litestar.channels import ChannelsPlugin


    @websocket("/ws")
    async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
        await socket.accept()
        async with channels.subscribe(["some_channel"]) as subscriber:
            async for message in subscriber.iter_events():
                await socket.send_data(message, mode="binary", encoding="ascii")


Managing subscriptions and sending
++++++++++++++++++++++++++++++++++

By running a worker task in the background taking care of the sending of events to the
socket, the application is free to interact with the socket in different ways, without
being blocked by a busy loop:

.. code-block:: python

    from litestar import websocket, WebSocket
    from litestar.channels import ChannelsPlugin


    @websocket("/ws")
    async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
        await socket.accept()

        async with channels.start_subscription(["channel"]) as subscriber:
            async with subscriber.run_in_background(socket):
                while True:
                    message = socket.receive_text()


Customizing how data is sent through a socket
---------------------------------------------

By default, data will be sent through a
:class:`WebSocket <litestar.connection.WebSocket>` using the
:meth:`send_data <litestar.connection.WebSocket.send_data>` method. This can be changed
by overriding :meth:`Subscriber.handle_socket_send`:


.. code-block:: python

    from litestar.channels import ChannelsPlugin, Subscriber
    from litestar import WebSocket
    from litestar.types.asgi_types import WebSocketMode


    class CustomSubscriber(Subscriber):
        async def handle_socket_send(
            self,
            socket: WebSocket,
            data: bytes,
            mode: WebSocketMode,
        ) -> None:
            await socket.send_data(data, mode=mode, encoding="utf-16")


    plugin = ChannelsPlugin(..., subscriber_class=CustomSubscriber)


Generating route handlers
-------------------------

A common pattern is to create a route handler per channel, sending data to the connected
client from that channel. This can be fully automated, using the plugin to create these
route handlers.

.. code-block:: python
    :caption: Setting ``create_route_handlers=True`` will create route handlers for all ``channels``

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend
    from litestar import Litestar


    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["foo", "bar"], create_route_handlers=True
    )

    app = Litestar(plugins=[channels_plugin])


The generated route handlers can optionally be configured to send the channel's history
after a client has connected:

.. code-block:: python
    :caption: Sending the first 10 history entries after a client connects

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend
    from litestar import Litestar

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(history=10),  # this number should be greater than
        # or equal to the history to be sent
        channels=["foo", "bar"],
        create_route_handlers=True,
        handler_send_history=10,
    )

    app = Litestar(plugins=[channels_plugin])


.. tip::

    When using the ``arbitrary_channels_allowed`` flag on the :class:`ChannelsPlugin`, a
    single route handler will be generated instead, using a
    :ref:`path parameter <usage/parameters:path parameter>` to specify the channel name



Managing backpressure
---------------------

Each subscriber manages its own backlog, i.e. a queue of messages it needs to send.
By default, this backlog is unlimited in size, allowing it to grow indefinitely. For
most applications, this should be no issue, but when the recipient consistently can't
process messages faster than they come in, an application might opt to handle this case.

The channels plugin provides two different strategies for managing this backpressure:

1. A backoff strategy, dropping newly incoming messages as long as the backlog is full
2. An eviction strategy, dropping the oldest message in the backlog when a new one is
   added while the backlog is full


.. code-block:: python
    :caption: Backoff strategy

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        max_backlog=1000,
        backlog_strategy="backoff",
    )


.. code-block:: python
    :caption: Eviction strategy

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        max_backlog=1000,
        backlog_strategy="dropleft",
    )


Backends
--------

The storing and fanout of messages is handled by a
:class:`ChannelsBackend <litestar.channels.base.ChannelsBackend>`. Currently implemented
are:

:class:`MemoryChannelsBacked <.memory.MemoryChannelsBackend>`
    A basic in-memory backend, mostly useful for testing and local development, but
    still fully capable. Since it stores all data in-process, it can achieve the highest
    performance of all the backends, but at the same time is not suitable for
    applications running on multiple processes.

:class:`RedisChannelsPubSubBackend <.redis.RedisChannelsPubSubBackend>`
    A Redis based backend, using `Pub/Sub <https://redis.io/docs/manual/pubsub/>`_ to
    delivery messages. This Redis backend has a low latency and overhead and is
    generally recommended if history is not needed

:class:`RedisChannelsStreamBackend <.redis.RedisChannelsStreamBackend>`
    A redis based backend, using `streams <https://redis.io/docs/data-types/streams/>`_
    to deliver messages. It has a slightly higher latency when publishing than the
    Pub/Sub backend, but achieves the same throughput in message fanout. Recommended
    when history is needed
