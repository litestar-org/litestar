================
处理机密信息
================

概述
----

有两种数据结构可用于帮助处理 Web 服务中的机密信息：
:class:`SecretString <datastructures.SecretString>` 和 :class:`SecretBytes <datastructures.SecretBytes>`。
这些是用于在应用程序中保存敏感数据的容器。

机密参数
--------

以下示例演示如何使用 :class:`~datastructures.SecretString` 在 GET 请求中接受机密值作为参数：

.. literalinclude:: /examples/datastructures/secrets/secret_header.py
    :language: python
    :caption: 使用 ``SecretString`` 处理 Header 参数的示例

.. note::

    在存储和比较机密信息时，请使用安全的做法来防止未经授权的访问。例如，使用环境变量、
    机密管理服务或加密数据库来安全地存储机密信息。在比较机密信息时，使用
    :func:`secrets.compare_digest` 或类似方法来减轻时序攻击的风险。

.. note::

    :class:`~connection.ASGIConnection` 对象的 :func:`headers <connection.ASGIConnection.headers>` 属性
    按照从 ASGI 消息解析的原样存储 headers。应注意确保这些 headers 不会以可能危及应用程序安全性的方式被记录或以其他方式暴露。

机密请求体
----------

此示例演示使用具有 :class:`~datastructures.SecretString` 字段的数据结构在请求的 HTTP 正文中接受机密信息：

.. literalinclude:: /examples/datastructures/secrets/secret_body.py
    :language: python
    :caption: 使用 ``SecretString`` 处理请求体的示例

安全注意事项
------------

虽然 :class:`SecretString` 和 :class:`SecretBytes` 可以帮助通过框架安全地传输机密数据，
但在应用程序中存储和比较机密信息时采用安全做法至关重要。以下是一些指导原则：

- 安全地存储机密信息，使用环境变量、机密管理服务或加密数据库。
- 始终使用恒定时间比较函数，如 :func:`secrets.compare_digest` 来比较机密值，
  以减轻时序攻击的风险。
- 实施访问控制和日志记录以监视和限制谁可以访问敏感信息。
