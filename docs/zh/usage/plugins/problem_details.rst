===============
Problem Details
===============

.. versionadded:: 2.9.0

Problem details 是一种标准化的方式，用于在 HTTP 响应中提供机器可读的错误详细信息，
如 `RFC 9457`_ 中所规定。

.. _RFC 9457: https://datatracker.ietf.org/doc/html/rfc9457

使用方法
--------

要发送 problem details 响应，应注册 ``ProblemDetailsPlugin``，
然后可以在任何地方引发 ``ProblemDetailsException``，它将自动转换为 problem details 响应。

.. literalinclude:: /examples/plugins/problem_details/basic_usage.py
    :language: python
    :caption: problem details 插件的基本用法

您可以通过在 ``ProblemDetailsConfig`` 中启用标志将所有 ``HTTPExceptions`` 转换为 problem details 响应。

.. literalinclude:: /examples/plugins/problem_details/convert_http_exceptions.py
    :language: python
    :caption: 将 ``HTTPException`` 转换为 problem details 响应

您还可以通过提供异常类型到可调用对象的映射，
将不是 ``HTTPException`` 的任何异常转换为 problem details 响应。

.. tip:: 这也可以用于覆盖 ``HTTPException`` 如何转换为 problem details 响应。

.. literalinclude:: /examples/plugins/problem_details/convert_exceptions.py
    :language: python
    :caption: 将自定义异常转换为 problem details 响应

.. warning:: 如果 ``extra`` 字段是 ``Mapping``，则它将合并到 problem details 响应中，否则它将包含在响应中，键为 ``extra``。
