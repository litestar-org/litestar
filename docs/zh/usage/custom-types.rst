自定义类型
============

数据序列化/反序列化（编码/解码）和验证是任何 API 框架的重要组成部分。

除了能够编码/解码和验证许多标准类型外，Litestar 还支持 Python 的内置 dataclasses 以及 Pydantic 和 msgspec 等库。

然而，有时您可能需要使用自定义类型。

使用类型编码器/解码器
------------------------------

Litestar 支持一种机制，您可以提供编码和解码钩子函数，将您的类型转换为它已知的类型。您可以通过 ``type_encoders`` 和 ``type_decoders`` :term:`参数 <parameter>` 提供它们，这些参数可以在每一层上定义。例如，请参阅 :doc:`litestar app 参考 </reference/app>`。

.. admonition:: 分层架构

    ``type_encoders`` 和 ``type_decoders`` 是 Litestar 分层架构的一部分，这意味着您可以在应用程序的每一层上设置它们。如果您在多个层上设置它们，最接近路由处理器的层将优先。

    您可以在这里阅读更多相关信息：
    :ref:`分层架构 <usage/applications:layered architecture>`

这是一个示例：

.. literalinclude:: /examples/encoding_decoding/custom_type_encoding_decoding.py
   :language: python
   :caption: 告诉 Litestar 如何编码和解码自定义类型

自定义 Pydantic 类型
---------------------

如果您使用自定义 Pydantic 类型，可以直接使用它：

.. literalinclude:: /examples/encoding_decoding/custom_type_pydantic.py
   :language: python
   :caption: 告诉 Litestar 如何编码和解码自定义 Pydantic 类型
