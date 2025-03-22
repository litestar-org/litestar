.. currentmodule:: litestar.channels

Channels
========

**Channels** are a group of related functionalities, built to facilitate the routing
of event streams, which for example can be used to broadcast messages to WebSocket
clients.

Channels provide:

1. Independent :term:`broker` backends, optionally handling inter-process communication
   and data persistence on demand
2. "Channel" based :term:`subscription` management
3. Subscriber objects as an abstraction over an individualized :term:`event stream`,
   providing background workers and managed subscriptions
4. Synchronous and asynchronous data publishing
5. Optional :term:`history` management on a per-:term:`channel` basis
6. :doc:`WebSocket </usage/websockets>` integration, generating WebSocket route
   handlers for an application, to handle the :term:`subscription` and publishing of incoming
   events to the connected client


Basic concepts
--------------

Utilizing Channels involves a few moving parts. To better familiarize with the concepts,
terminology, and the flow of data, the following glossary and flowcharts are provided

Glossary
++++++++

.. dropdown:: Click to toggle the glossary

    .. glossary::

        event
            A single piece of data published to, or received from a :term:`backend` bound
            to the :term:`channel` it was originally published to

        event stream
            A stream of :term:`events <event>`, consisting of events from all the channels a
            :term:`Subscriber` has previously subscribed to

        subscriber
            A :class:`Subscriber <.subscriber.Subscriber>`: An object wrapping an
            :term:`event stream` and providing access to it through various methods

        backend
            A :class:`ChannelsBackend <.backends.base.ChannelsBackend>`. This object
            manages communication between the plugin and the :term:`broker`, publishing
            messages to and receiving messages from it. Each plugin instance is associated
            with exactly one backend.

        broker
            Responsible for receiving and publishing messages to all connected
            :term:`backends <backend>`; All backends sharing the same broker will have
            access to the same messages, allowing for inter-process communication. This is
            typically handled by a separate entity like `Redis <https://redis.io/>`_

        plugin
            The :class:`~.plugin.ChannelsPlugin`, a central instance
            managing :term:`subscribers <subscriber>`, reading messages from the
            :term:`backend`, putting them in the appropriate :term:`event stream`, and
            publishing data to the backend

        channel
            A named group of subscribers, to which data can be published. Subscribers can
            subscribe to multiple channels, and channels can have multiple subscribers

        subscription
            A connection between a :term:`subscriber` and a :term:`channel`, allowing the
            subscriber to receive events from the channel

        backpressure
            A mechanism to prevent the backlog of a :term:`subscriber` from growing
            indefinitely, by either dropping new messages or evicting old ones

        history
            A set of previously published :term:`events <event>`, stored by the :term:`backend`
            and available to be pushed to a :term:`subscriber`

        fanout
            The process of sending a message to all subscribers of a channel

        eviction
            A :term:`backpressure` strategy, dropping the oldest message in the backlog when
            a new one is added while the backlog is full

        backoff
            A :term:`backpressure` strategy, dropping newly incoming messages as long as the
            backlog is full

Flowcharts
++++++++++

.. dropdown:: Click to toggle flowcharts

    .. mermaid::
        :align: center
        :caption: Publishing flow from the application to the :term:`broker`

        flowchart LR
            Backend(Backend) --> Broker[(Broker)]

            Plugin{{Plugin}} --> Backend

            Application[[Application]] --> Plugin

    .. mermaid::
        :align: center
        :caption: Fanout flow of data from the :term:`broker` to the sockets, showing multiple plugin instances

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

The :class:`ChannelsPlugin`
---------------------------

.. currentmodule:: litestar.channels.plugin

The :class:`ChannelsPlugin` acts as the central entity for managing channels and subscribers.
It is used to publish messages, control how data is stored, and manage :term:`subscribers <subscriber>`,
route handlers, and configuration.

.. tip:: The plugin makes itself available as a dependency under the :paramref:`~ChannelsPlugin.channels` key, which
    means it is not necessary to import it and instead, it can be used from within route handlers or other callables
    within the dependency tree directly

Configuring the :term:`channels <channel>`
++++++++++++++++++++++++++++++++++++++++++

The :term:`channels <channel>` managed by the plugin can be either defined upfront, passing them to the
:paramref:`~ChannelsPlugin.channels` parameter, or created "on the fly"
(i.e., on the first :term:`subscription` to a channel) by setting
:paramref:`~ChannelsPlugin.arbitrary_channels_allowed` to ``True``.

.. code-block:: python
    :caption: Passing channels explicitly

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., channels=["foo", "bar"])

.. code-block:: python
    :caption: Allowing arbitrary channels

    from litestar.channels import ChannelsPlugin

    channels_plugin = ChannelsPlugin(..., arbitrary_channels_allowed=True)

If :paramref:`~ChannelsPlugin.arbitrary_channels_allowed` is not ``True``, trying to publish or subscribe to a
:term:`channel` not passed to :paramref:`~ChannelsPlugin.channels` will raise a :exc:`ChannelsException`.

Publishing data
+++++++++++++++

One of the core aspects of the plugin is publishing data, which is done through its
:meth:`~ChannelsPlugin.publish` method:

.. code-block:: python
    :caption: Publishing data to a channel with :meth:`~ChannelsPlugin.publish`

    channels.publish({"message": "Hello"}, "general")

The above example will publish the data to the channel ``general``, subsequently putting
it into all subscriber's :term:`event stream` to be consumed.

This method is non-blocking, even though channels and the associated
:term:`backends <backend>` are fundamentally asynchronous.

Calling :meth:`~ChannelsPlugin.publish` effectively enqueues a message to be sent to the backend, from which
follows that there is no guarantee that an event will be available in the backend immediately after this call.

Alternatively, the asynchronous :meth:`~ChannelsPlugin.wait_published` method can be used, which skips the
internal message queue, publishing the data to the backend directly.

.. note::
    While calling :meth:`~ChannelsPlugin.publish` does not guarantee the
    message is sent to the backend immediately, it will be sent there *eventually*; On
    shutdown, the plugin will wait for all queues to empty

Managing :term:`subscriptions <subscription>`
+++++++++++++++++++++++++++++++++++++++++++++

Another core functionality of the plugin is managing :term:`subscriptions <subscription>`, for which two
different approaches exist:

1. Manually through the :meth:`~ChannelsPlugin.subscribe` and :meth:`~ChannelsPlugin.unsubscribe` methods
2. By using the :meth:`~ChannelsPlugin.start_subscription` context manager

Both :meth:`~ChannelsPlugin.subscribe` and :meth:`~ChannelsPlugin.start_subscription` produce a :class:`Subscriber`,
which can be used to interact with the streams of events subscribed to.

The context manager should be preferred, since it ensures that channels are being unsubscribed.
Using the :meth:`~ChannelsPlugin.subscribe` and :meth:`~ChannelsPlugin.unsubscribe` methods directly should only be
one when a :term:`context manager <asynchronous context manager>` cannot be used, e.g., when the :term:`subscription`
would span different contexts.

.. code-block:: python
    :caption: Calling the :term:`subscription` methods manually

    subscriber = await channels.subscribe(["foo", "bar"])
    try:
        ...  # do some stuff here
    finally:
        await channels.unsubscribe(subscriber)

.. code-block:: python
    :caption: Using the :term:`async context manager <asynchronous context manager>`

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # do some stuff here

It is also possible to unsubscribe from individual :term:`channels <channel>`, which may be desirable if
:term:`subscriptions <subscription>` need to be managed dynamically.

.. code-block:: python
    :caption: Unsubscribing from a channel manually

    subscriber = await channels.subscribe(["foo", "bar"])
    try:
        ...  # do some stuff here
    finally:
        await channels.unsubscribe(subscriber, ["foo"])


Or, using the context manager

.. code-block:: python
    :caption: Using the :term:`async context manager <asynchronous context manager>` to unsubscribe from a
      :term:`channel`

    async with channels.start_subscription(["foo", "bar"]) as subscriber:
        ...  # do some stuff here
        await channels.unsubscribe(subscriber, ["foo"])

Managing :term:`history`
++++++++++++++++++++++++

Some backends support per-:term:`channel` :term:`history`, keeping a certain amount of :term:`events <event>` in storage.
This :term:`history` can then be pushed to a :term:`subscriber`.

The plugin's :meth:`put_subscriber_history <ChannelsPlugin.put_subscriber_history>` can
be used to fetch this :term:`history` and put it into a subscriber's :term:`event stream`.

.. literalinclude:: /examples/channels/put_history.py
    :caption: Retrieving :term:`channel` :term:`history` for a :term:`subscriber` and putting it into the
      :term:`stream <event stream>`

.. note::
    The publication of the :term:`history` happens sequentially, one :term:`channel` and one
    :term:`event` at a time. This is done to ensure the correct ordering of events and to avoid
    filling up a :term:`subscriber`'s backlog, which would result in dropped :term:`history` entries. Should the
    amount of entries exceed the maximum backlog size, the execution will wait until
    previous events have been processed.

   Read more: `Managing backpressure`_

The :class:`Subscriber`
-----------------------

.. py:currentmodule:: litestar.channels.subscriber

The :class:`Subscriber` manages an individual :term:`event stream`, provided to it by the plugin,
representing the sum of events from all :term:`channels <channel>` the subscriber has subscribed to.

It can be considered the endpoint of all :term:`events <event>`, while the backends act as the source,
and the plugin as a router, being responsible for supplying events gathered from the
backend into the appropriate subscriber's streams.

In addition to being an abstraction of an :term:`event stream`, the :class:`Subscriber`
provides two methods to handle this stream:

:meth:`iter_events <Subscriber.iter_events>`
    An :term:`asynchronous generator`, producing one event from the stream at a time, waiting
    until the next one becomes available

:meth:`run_in_background <Subscriber.run_in_background>`
    A :term:`context manager <asynchronous context manager>`, wrapping an :class:`asyncio.Task`,
    consuming events yielded by :meth:`iter_events <Subscriber.iter_events>`, invoking a provided :term:`callback`
    for each of them. Upon exit, it will attempt a graceful shutdown of the running task, waiting
    for all currently enqueued events in the stream to be processed.
    If the context exits with an error, the task will be cancelled instead.

    It is possible to force the task to stop immediately, by setting :paramref:`~Subscriber.run_in_background.join`
    to ``False`` in :meth:`run_in_background <Subscriber.run_in_background>`, which will lead to the cancellation of
    the task. By default this only happens when the context is left with an exception.

.. important::
    The :term:`events <event>` in the :term:`event streams <event stream>` are always
    bytes; When calling :meth:`ChannelsPlugin.publish`, data will be serialized before
    being sent to the backend.

Consuming the :term:`event stream`
++++++++++++++++++++++++++++++++++

There are two general methods of consuming the :term:`event stream`:

1. By iterating over it directly, using :meth:`iter_events <Subscriber.iter_events>`
2. By using the :meth:`run_in_background <Subscriber.run_in_background>` context manager,
   which starts a background task, iterating over the stream, invoking a provided
   callback for every :term:`event` received

Iterating over the :term:`stream <event stream>` directly is mostly useful if processing the events is the only
concern, since :meth:`iter_events <Subscriber.iter_events>` is effectively an infinite
loop. For all other applications, using the context manager is preferable, since it
allows to easily run other code concurrently.

.. literalinclude:: /examples/channels/iter_stream.py
    :caption: Iterating over the :term:`event stream` to send data to a WebSocket

In the above example, the stream is used to send data to a
:class:`WebSocket <litestar.connection.WebSocket>`.

The same can be achieve by passing :meth:`Websocket.send_text() <litestar.connection.WebSocket.send_text>` as the
callback to :meth:`~Subscriber.run_in_background`. This will cause the WebSocket's method to be invoked every time
a new :term:`event` becomes available in the :term:`stream <event stream>`, but gives control back to the application,
providing an opportunity to perform other tasks, such as receiving incoming data from the socket.

.. literalinclude:: /examples/channels/run_in_background.py
    :caption: Using :meth:`~Subscriber.run_in_background` to process events concurrently

.. important:: Iterating over :meth:`~Subscriber.iter_events` should be approached
    with caution when being used together with WebSockets.

    Since :exc:`WebSocketDisconnect` is only raised after the corresponding ASGI event
    has been *received*, it can result in an indefinitely suspended coroutine. This can
    happen if for example the client disconnects, but no further events are received.
    The generator will then wait for new events, but since it will never receive any,
    no ``send`` call on the WebSocket will be made, which in turn means no exception
    will be raised to break the loop.

Managing :term:`backpressure`
-----------------------------

Each subscriber manages its own backlog: A queue of unprocessed :term:`events <event>`.
By default, this backlog is unlimited in size, allowing it to grow indefinitely. For
most applications, this should be no issue, but when the recipient consistently can not
process messages faster than they come in, an application might opt to handle this case.

The channels plugin provides two different strategies for managing this :term:`backpressure`:

1. A :term:`backoff` strategy, dropping newly incoming messages as long as the backlog is full
2. An :term:`eviction` strategy, dropping the oldest message in the backlog when a new one is
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
    :caption: :term:`Eviction <eviction>` strategy

    from litestar.channels import ChannelsPlugin
    from litestar.channels.memory import MemoryChannelsBackend

    channels = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        max_backlog=1000,
        backlog_strategy="dropleft",
    )

Backends
--------

The storing and :term:`fanout` of messages is handled by a
:class:`ChannelsBackend <litestar.channels.backends.base.ChannelsBackend>`.

The following backends are currently implemented:

:class:`MemoryChannelsBacked <.memory.MemoryChannelsBackend>`
    A basic in-memory backend, mostly useful for testing and local development, but
    still fully capable. Since it stores all data in-process, it can achieve the highest
    performance of all the backends, but at the same time is not suitable for
    applications running on multiple processes.

:class:`RedisChannelsPubSubBackend <.redis.RedisChannelsPubSubBackend>`
    A Redis based backend, using `Pub/Sub <https://redis.io/docs/manual/pubsub/>`_ to
    delivery messages. This Redis backend has a low latency and overhead and is
    generally recommended if :term:`history` is not needed

:class:`RedisChannelsStreamBackend <.redis.RedisChannelsStreamBackend>`
    A redis based backend, using `streams <https://redis.io/docs/data-types/streams/>`_
    to deliver messages. It has a slightly higher latency when publishing than the
    Pub/Sub backend, but achieves the same throughput in message :term:`fanout`. Recommended
    when :term:`history` is needed

:class:`AsyncPgChannelsBackend <.asyncpg.AsyncPgChannelsBackend>`
    A postgres backend using the `asyncpg <https://magicstack.github.io/asyncpg/current/>`_ driver

:class:`PsycoPgChannelsBackend <.psycopg.PsycoPgChannelsBackend>`
    A postgres backend using the `psycopg3 <https://www.psycopg.org/psycopg3/docs/>`_ async driver

Integrating with websocket handlers
-----------------------------------

Generating route handlers
+++++++++++++++++++++++++

A common pattern is to create a route handler per :term:`channel`, sending data to the connected
client from that channel. This can be fully automated, using the plugin to create these route handlers.

.. literalinclude:: /examples/channels/create_route_handlers.py
    :language: python
    :caption: Setting ``create_ws_route_handlers=True`` will create route handlers for all ``channels``

The generated route handlers can optionally be configured to send the :term:`channel`'s :term:`history`
after a client has connected:

.. literalinclude:: /examples/channels/create_route_handlers_send_history.py
    :caption: Sending the first 10 :term:`history` entries after a client connects

.. tip:: When using the :paramref:`~litestar.channels.plugin.ChannelsPlugin.arbitrary_channels_allowed` parameter
    on the :class:`ChannelsPlugin`, a single route handler will be generated instead, using a
    :ref:`path parameter <usage/routing/parameters:path parameters>` to specify the channel name
