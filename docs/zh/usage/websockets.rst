WebSockets
==========

在 Litestar 中有三种处理 WebSocket 的方法：

1. 低级 :func:`~litestar.handlers.websocket` 路由处理程序，在 ASGI WebSocket 接口上提供基本抽象
2. :func:`~litestar.handlers.websocket_listener` 和 :class:`~litestar.handlers.WebsocketListener`\  ：反应式、事件驱动的 WebSocket，具有完整的序列化和 DTO 支持以及对同步接口的支持
3. :func:`~litestar.handlers.websocket_stream`：主动的、面向流的 WebSocket，具有完整的序列化和 DTO 支持
4. :func:`~litestar.handlers.send_websocket_stream`：主动的、面向流的 WebSocket


低级和高级接口之间的主要区别在于，处理低级接口需要设置循环并监听传入数据、处理异常、客户端断开连接以及解析传入和序列化传出数据。



WebSocket 监听器
--------------------

WebSocket 监听器可用于以事件驱动的方式与 WebSocket 交互，使用回调式接口。它们将 WebSocket 处理程序视为任何其他路由处理程序：接受已预处理形式的传入数据并返回要序列化并通过连接发送的数据的可调用对象。低级细节将在幕后处理。


.. code-block:: python

    from litestar import Litestar
    from litestar.handlers.websocket_handlers import websocket_listener


    @websocket_listener("/")
    async def handler(data: str) -> str:
        return data


    app = Litestar([handler])


此处理程序将接受 ``/`` 上的连接，并等待接收数据。一旦收到消息，它将通过 ``data`` 参数传递到定义的处理程序函数中。这像常规路由处理程序一样工作，因此可以指定应接收的数据类型，并将相应地转换。

.. note::
    与 WebSocket 路由处理程序相反，使用 :func:`websocket_listener <.handlers.websocket_listener>` 装饰的函数不必是异步的。



接收数据
++++++++++++++

可以通过 ``data`` 参数在监听器中接收数据。传递给此参数的数据将根据给定的类型注释进行转换/解析，并支持 :class:`str`、:class:`bytes` 或任意 :class:`dict` / 或 :class:`list` 形式的 JSON。

.. important::

    除非 `data` 用 `str` 或 `bytes` 注释，否则监听器将默认为 JSON


.. tab-set::

    .. tab-item:: JSON

        .. literalinclude:: /examples/websockets/receive_json.py
            :language: python


    .. tab-item:: 文本

        .. literalinclude:: /examples/websockets/receive_str.py
            :language: python


    .. tab-item:: 字节

        .. literalinclude:: /examples/websockets/receive_bytes.py
            :language: python


.. important::

    与路由处理程序相反，JSON 数据只会被解析但不会被验证。这是当前实现的限制，将在未来版本中更改。


发送数据
+++++++++++++

通过从处理函数简单地返回要发送的值来发送数据。与接收数据类似，类型注释配置如何处理数据。不是 :class:`str` 或 :class:`bytes` 的值被假定为 JSON 可编码，并将在发送之前相应地序列化。此序列化可用于 Litestar 当前支持的所有数据类型（:doc:`dataclasses <python:library/dataclasses>`\ 、:class:`TypedDict <typing.TypedDict>`、:class:`NamedTuple <typing.NamedTuple>`、:class:`msgspec.Struct` 等），包括 DTO。


.. tab-set::

    .. tab-item:: 文本

        .. literalinclude:: /examples/websockets/sending_str.py
            :language: python

    .. tab-item:: 字节

        .. literalinclude:: /examples/websockets/sending_bytes.py
            :language: python

    .. tab-item:: Dict 作为 JSON

        .. literalinclude:: /examples/websockets/sending_json_dict.py
            :language: python


    .. tab-item:: Dataclass 作为 JSON

        .. literalinclude:: /examples/websockets/sending_json_dataclass.py
            :language: python


设置传输模式
+++++++++++++++++++++++


接收模式
~~~~~~~~~~~~

.. tab-set::

    .. tab-item:: 文本模式

        ``text`` 是默认模式，适用于大多数消息，包括结构化数据如 JSON。

        .. literalinclude:: /examples/websockets/mode_receive_text.py
            :language: python


    .. tab-item:: 二进制模式

        .. literalinclude:: /examples/websockets/mode_receive_binary.py
            :language: python


.. important::
    一旦配置了模式，监听器将只监听适当类型的套接字事件。这意味着如果监听器配置为使用 ``binary`` 模式，它将不会响应在文本通道中发送数据的 WebSocket 事件。


发送模式
~~~~~~~~~

.. tab-set::

    .. tab-item:: 文本模式

        ``text`` 是默认模式，适用于大多数消息，包括结构化数据如 JSON。

        .. literalinclude:: /examples/websockets/mode_send_text.py
            :language: python


    .. tab-item:: 二进制模式

        .. literalinclude:: /examples/websockets/mode_send_binary.py
            :language: python




依赖注入
++++++++++++++++++++

:doc:`dependency-injection` 可用并且通常与常规路由处理程序的工作方式相同：

.. literalinclude:: /examples/websockets/dependency_injection_simple.py
    :language: python


.. important::
    注入的依赖在底层 **路由处理程序** 级别工作。这意味着每次调用监听器函数时都不会重新评估它们。

以下示例利用 :ref:`yield 依赖 <yield_dependencies>` 和依赖只对每个连接评估一次的事实；``yield`` 后的步骤仅在连接关闭后执行。


.. literalinclude:: /examples/websockets/dependency_injection_yield.py
    :language: python



直接与 WebSocket 交互
+++++++++++++++++++++++++++++++++++++++

有时需要访问套接字实例，在这种情况下，可以通过 ``socket`` 参数将 :class:`WebSocket <.connection.WebSocket>` 实例注入到处理函数中：

.. literalinclude:: /examples/websockets/socket_access.py
    :language: python


.. important::
    由于 WebSocket 本质上是异步的，要与 :class:`WebSocket <.connection.WebSocket>` 上的异步方法交互，处理函数需要是异步的。


自定义连接接受
+++++++++++++++++++++++++++++++++

默认情况下，Litestar 将通过等待不带参数的 ``WebSocket.accept()`` 接受所有传入连接。可以通过传递自定义 ``connection_accept_handler`` 函数来自定义此行为。Litestar 将等待此函数接受连接。

.. literalinclude:: /examples/websockets/setting_custom_connection_headers.py
    :language: python


基于类的 WebSocket 处理
++++++++++++++++++++++++++++++

除了使用上面示例中的简单函数外，通过扩展 :class:`WebSocketListener <.handlers.WebsocketListener>` 可以实现基于类的方法。这提供了方便地访问套接字事件（如连接和断开连接），并可用于封装更复杂的逻辑。


.. tab-set::

    .. tab-item:: 同步

        .. literalinclude:: /examples/websockets/listener_class_based.py
            :language: python

    .. tab-item:: 异步

        .. literalinclude:: /examples/websockets/listener_class_based_async.py
            :language: python


自定义 WebSocket
++++++++++++++++

.. versionadded:: 2.7.0

Litestar 支持自定义 ``websocket_class`` 实例，可用于进一步配置默认 :class:`WebSocket`。下面的示例说明了如何为整个应用程序实现自定义 WebSocket 类。

.. dropdown:: 应用程序级别的自定义 websocket 示例

    .. literalinclude:: /examples/websockets/custom_websocket.py
        :language: python

.. admonition:: 分层架构

   WebSocket 类是 Litestar 分层架构的一部分，这意味着您可以在应用程序的每一层设置 WebSocket 类。如果您在多个层上设置了 WebSocket 类，则最接近路由处理程序的层将优先。

   您可以在 :ref:`usage/applications:layered architecture` 部分阅读更多相关信息


WebSocket 流
-----------------

WebSocket 流可用于主动向客户端推送数据，使用异步生成器函数。每次生成器 ``yield`` 时，数据将通过套接字发送，直到它耗尽或客户端断开连接。

.. literalinclude:: /examples/websockets/stream_basic.py
    :language: python
    :caption: 以 0.5 秒间隔流式传输当前时间


序列化
+++++++++++++

就像路由处理程序一样，类型注释配置如何处理数据。:class:`str` 或 :class:`bytes` 将按原样发送，而其他所有内容将在发送之前编码为 JSON。此序列化可用于 Litestar 当前支持的所有数据类型（:doc:`dataclasses <python:library/dataclasses>`、:class:`TypedDict <typing.TypedDict>`、:class:`NamedTuple <typing.NamedTuple>`、:class:`msgspec.Struct` 等），包括 DTO。


依赖注入
++++++++++++++++++++

依赖注入可用并且类似于常规路由处理程序工作。

.. important::
    特别是对于长期存在的流，要记住的一件事是依赖的作用域为处理程序的生命周期。这意味着，如果例如在依赖中获取数据库连接，它将被保持直到生成器停止。这在所有情况下可能都不是理想的，在生成器本身内部临时获取资源可能更可取

    .. literalinclude:: /examples/websockets/stream_di_hog.py
        :language: python
        :caption: 坏：锁将被保持直到客户端断开连接


    .. literalinclude:: /examples/websockets/stream_di_hog_fix.py
        :language: python
        :caption: 好：锁只在需要时才会被获取


直接与 WebSocket 交互
+++++++++++++++++++++++++++++++++++++++

要直接与 :class:`WebSocket <.connection.WebSocket>` 交互，可以通过 ``socket`` 参数将其注入到生成器函数中：

.. literalinclude:: /examples/websockets/stream_socket_access.py
    :language: python


流式传输时接收数据
++++++++++++++++++++++++++++++

默认情况下，流将在后台监听客户端断开连接，并在收到后停止生成器。由于这需要从套接字接收数据，如果应用程序同时尝试从同一套接字读取，则可能导致数据丢失。

.. tip::
    为了防止数据丢失，默认情况下，``websocket_stream`` 如果在监听客户端断开连接时接收到任何数据，将引发异常。如果应该忽略传入数据，则应将 ``allow_data_discard`` 设置为 ``True``

如果在流式传输时需要接收数据，可以通过设置 ``listen_for_disconnect=False`` 将 :func:`~litestar.handlers.send_websocket_stream` 配置为不监听断开连接。

.. important::
    使用 ``listen_for_disconnect=False`` 时，应用程序需要确保在其他地方接收断开连接事件，否则流只会在生成器耗尽时终止


组合流式传输和接收数据
---------------------------------------

要同时流式传输和接收数据，可以使用 :func:`~litestar.handlers.send_websocket_stream` 结合 :class:`~litestar.handlers.websocket` 处理程序或 WebSocket 监听器手动设置流。

.. tab-set::

    .. tab-item:: websocket_listener

        .. tab-set::

            .. tab-item:: 示例

                .. literalinclude:: /examples/websockets/stream_and_receive_listener.py
                    :language: python

            .. tab-item:: 如何测试

                .. literalinclude:: ../../tests/examples/test_websockets.py
                    :language: python
                    :lines: 18-25


    .. tab-item:: websocket handler

        .. tab-set::

            .. tab-item:: 示例

                .. literalinclude:: /examples/websockets/stream_and_receive_raw.py
                    :language: python

            .. tab-item:: 如何测试

                .. literalinclude:: ../../tests/examples/test_websockets.py
                    :language: python
                    :lines: 28-35

传输模式
---------------

WebSocket 有两种传输模式：``text`` 和 ``binary``。它们决定了字节如何通过线路传输，并且可以彼此独立设置，即套接字可以发送 ``binary`` 并接收 ``text``


直觉上似乎 ``text`` 和 ``binary`` 应该分别映射到 :class:`str` 和 :class:`bytes`，但事实并非如此。WebSocket 可以以任何格式接收和发送数据，独立于模式。模式仅影响传输期间（即在协议级别）如何处理字节。在大多数情况下，默认模式 - ``text`` - 就是所需的全部。二进制传输通常在发送没有有意义的字符串表示的二进制 blob（例如图像）时使用。
