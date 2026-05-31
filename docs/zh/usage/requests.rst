请求
========

请求体
------------

可以使用处理函数中的特殊 ``data`` 参数来访问 HTTP 请求的主体。

.. literalinclude:: /examples/request_data/request_data_1.py
    :language: python


``data`` 的类型可以是任何支持的类型，包括


* 任意标准库类型
* :class:`TypedDicts <typing.TypedDict>`
* :func:`dataclasses <dataclasses.dataclass>`
* 通过 :doc:`插件 </usage/plugins/index>` 支持的类型，即
    - `Msgspec Struct <https://jcristharif.com/msgspec/structs.html>`_
    - `Pydantic 模型 <https://docs.pydantic.dev/usage/models/>`_
    - `Attrs 类 <https://www.attrs.org/en/stable/>`_


.. literalinclude:: /examples/request_data/request_data_2.py
    :language: python


验证和自定义 OpenAPI 文档
-----------------------------------------------------

借助 :class:`Body <litestar.params.Body>`，您可以对请求体的验证进行细粒度控制，还可以自定义 OpenAPI 文档：


.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_3.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 35-41


内容类型
------------

默认情况下，Litestar 会尝试将请求体解析为 JSON。虽然在大多数情况下这可能是期望的，但您可能想要指定不同的类型。您可以通过将 :class:`RequestEncodingType <litestar.enums.RequestEncodingType>` 传递给 ``Body`` 来实现。这也将有助于在 OpenAPI 模式中生成正确的媒体类型。

URL 编码表单数据
^^^^^^^^^^^^^^^^^^^^^

要访问作为 `url 编码表单数据 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_ 发送的数据，即 ``application/x-www-form-urlencoded`` Content-Type 标头，使用 :class:`Body <litestar.params.Body>` 并指定 :class:`RequestEncodingType.URL_ENCODED <litestar.enums.RequestEncodingType>` 作为 ``media_type``：

.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_4.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 44-48

.. note::

    URL 编码数据本质上不如 JSON 数据通用 - 例如，它无法处理复杂的字典和深度嵌套的数据。它应该只用于简单的数据结构。


MultiPart 表单数据
^^^^^^^^^^^^^^^^^^^

您可以通过在 :class:`Body <litestar.params.Body>` 函数中指定来访问使用 `multipart/form-data <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_ Content-Type 标头的请求上传的数据：

.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_5.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 51-64


文件上传
------------

对于上传的文件，Litestar 将结果转换为 :class:`UploadFile <.datastructures.upload_file.UploadFile>` 类的实例，该类提供了使用文件的便捷接口。因此，您需要相应地输入文件上传的类型。

要访问单个文件，只需将 ``data`` 类型设置为 :class:`UploadFile <.datastructures.upload_file.UploadFile>`：


.. tab-set::

    .. tab-item:: 异步

        .. tab-set::

            .. tab-item:: 示例

                .. literalinclude:: /examples/request_data/request_data_6.py
                    :language: python

            .. tab-item:: 如何测试

                .. literalinclude:: ../../tests/examples/test_request_data.py
                    :language: python
                    :lines: 67-71

    .. tab-item:: 同步

        .. tab-set::

            .. tab-item:: 示例

                .. literalinclude:: /examples/request_data/request_data_7.py
                    :language: python

            .. tab-item:: 如何测试

                .. literalinclude:: ../../tests/examples/test_request_data.py
                    :language: python
                    :lines: 74-78

.. admonition:: 技术细节
    :class: info

    :class:`UploadFile <.datastructures.UploadFile>` 包装了 :class:`SpooledTemporaryFile <tempfile.SpooledTemporaryFile>`，因此可以异步使用。在同步函数中，我们不需要这个包装器，因此可以直接使用其 :meth:`read <io.TextIOBase.read>` 方法。



多个文件
^^^^^^^^^^^^^^

要访问具有已知文件名的多个文件，您可以使用 pydantic 模型：


.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_8.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 81-87


文件作为字典
^^^^^^^^^^^^^^^^^^^^^

如果您不关心解析和验证，只想将表单数据作为字典访问，则可以使用 ``dict``：

.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_9.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 90-97


文件作为列表
^^^^^^^^^^^^^^^

最后，您还可以在没有文件名的情况下将文件作为列表访问：

.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/request_data_10.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 100-133

MessagePack 数据
----------------

要接收 `MessagePack <https://msgpack.org/>`_ 数据，通过使用 :class:`RequestEncodingType.MESSAGEPACK <.enums.RequestEncodingType>` 为 ``Body`` 指定适当的 ``Content-Type``：

.. tab-set::

    .. tab-item:: 示例

        .. literalinclude:: /examples/request_data/msgpack_request.py
            :language: python

    .. tab-item:: 如何测试

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 136-141

自定义请求
--------------

.. versionadded:: 2.7.0

Litestar 支持自定义 ``request_class`` 实例，可用于进一步配置默认的 :class:`Request`。
下面的示例说明了如何为整个应用程序实现自定义请求类。

.. dropdown:: 应用程序级别的自定义请求示例

    .. tab-set::

        .. tab-item:: 示例

            .. literalinclude:: /examples/request_data/custom_request.py
                :language: python

        .. tab-item:: 如何测试

            .. literalinclude:: ../../tests/examples/test_request_data.py
                :language: python
                :lines: 144-147

.. admonition:: 分层架构

   请求类是 Litestar 分层架构的一部分，这意味着您可以在应用程序的每一层上设置请求类。如果您在多个层上设置了请求类，则最接近路由处理程序的层将优先。

   您可以在 :ref:`usage/applications:layered architecture` 部分阅读更多相关信息


限制
-------

主体大小
^^^^^^^^^^

可以通过 ``request_max_body_size`` 参数在所有层上设置允许的请求体大小限制，默认为 10MB。如果请求体超过此限制，将返回 ``413 - Request Entity Too Large`` 响应。此限制适用于所有消费请求体的方法，包括通过路由处理程序中的 ``body`` 参数请求它，以及通过手动构造的 :class:`~litestar.connection.Request` 实例（例如在中间件中）消费它。

要对特定处理程序/路由器/控制器禁用此限制，可以将其设置为 :obj:`None`。

.. danger::
    强烈不建议设置 ``request_max_body_size=None``，因为它会通过向受影响的端点发送任意大的请求体来使应用程序面临拒绝服务 (DoS) 攻击。由于 Litestar 必须读取整个主体才能执行某些操作，例如解析 JSON，如果没有外部限制，它将填满所有可用内存/交换空间，直到应用程序/服务器崩溃。

    通常只建议在应用程序运行在反向代理（如 NGINX）后面的环境中使用，其中已设置了大小限制。


.. danger::
    由于 ``request_max_body_size`` 是按请求处理的，因此当中间件或 ASGI 处理程序尝试通过原始 ASGI 事件访问请求体时，它不会影响它们。为避免这种情况，中间件和 ASGI 处理程序应构造 :class:`~litestar.connection.Request` 实例并使用常规 :meth:`~litestar.connection.Request.stream` / :meth:`~litestar.connection.Request.body` 或内容适当的方法以安全的方式消费请求体。


.. tip::
    对于定义 ``Content-Length`` 标头的请求，如果标头值超过 ``request_max_body_size``，Litestar 将不会尝试读取请求体。

    如果标头值在允许的范围内，Litestar 将在流式传输请求体期间验证它不超过标头中指定的大小。如果请求超过此大小，它将中止请求并返回 ``400 - Bad Request``。
