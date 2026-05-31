异常和异常处理
=================================

Litestar 定义了一个名为 :class:`LitestarException <litestar.exceptions.LitestarException>` 的基础异常，它作为所有其他异常的基类，请参阅 :mod:`API 参考 <litestar.exceptions>`。

一般来说，Litestar 有两种异常处理场景：

- 在应用程序配置、启动和初始化期间引发的异常，这些异常像常规 Python 异常一样处理
- 作为请求处理的一部分引发的异常，即路由处理器、依赖项和中间件中的异常，应作为响应返回给最终用户

配置异常
------------------------

对于缺少额外依赖项，Litestar 将引发 :class:`MissingDependencyException <litestar.exceptions.MissingDependencyException>`。例如，如果您尝试使用 :ref:`SQLAlchemyPlugin <plugins>` 而没有安装 SQLAlchemy，则在启动应用程序时将引发此异常。

对于其他配置问题，Litestar 将引发 :class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>`，并带有解释问题的消息。

应用程序异常
----------------------

对于应用程序异常，Litestar 使用 :class:`~litestar.exceptions.http_exceptions.HTTPException` 类，它继承自 :class:`~litestar.exceptions.LitestarException`。此异常将被序列化为以下模式的 JSON 响应：

.. code-block:: json

   {
     "status_code": 500,
     "detail": "Internal Server Error",
     "extra": {}
   }

Litestar 还提供了几个预配置的 ``HTTPException`` 子类，这些子类具有预设的错误代码，您可以使用，例如：


.. :currentmodule:: litestar.exceptions.http_exceptions

+----------------------------------------+-------------+------------------------------------------+
| 异常                                   | 状态码      | 描述                                     |
+========================================+=============+==========================================+
| :class:`ImproperlyConfiguredException` | 500         | 内部用于配置错误                         |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ValidationException`           | 400         | 在验证或解析失败时引发                   |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotAuthorizedException`        | 401         | HTTP 状态码 401                          |
+----------------------------------------+-------------+------------------------------------------+
| :class:`PermissionDeniedException`     | 403         | HTTP 状态码 403                          |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotFoundException`             | 404         | HTTP 状态码 404                          |
+----------------------------------------+-------------+------------------------------------------+
| :class:`InternalServerException`       | 500         | HTTP 状态码 500                          |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ServiceUnavailableException`   | 503         | HTTP 状态码 503                          |
+----------------------------------------+-------------+------------------------------------------+

.. :currentmodule:: None

当值验证失败时，结果将是 :class:`~litestar.exceptions.http_exceptions.ValidationException`，其中 ``extra`` 键设置为验证错误消息。

.. warning:: 默认情况下，所有验证错误消息都将提供给 API 使用者。如果这不是您的意图，请调整异常内容。


异常处理
------------------

默认情况下，Litestar 通过将所有错误转换为 **JSON 响应** 来处理它们。如果错误是 :class:`~litestar.exceptions.http_exceptions.HTTPException` 的 **实例**，则响应将包含适当的 ``status_code``。否则，响应将默认为 ``500 - "Internal Server Error"``。


例如，以下处理程序将默认为 ``MediaType.TEXT``，因此异常将作为文本引发。

.. literalinclude:: /examples/exceptions/implicit_media_type.py
    :language: python

您可以通过传递一个字典来自定义异常处理，该字典将状态码或异常类映射到可调用对象。例如，如果您想用返回纯文本响应的处理程序替换默认异常处理程序，您可以这样做：

.. literalinclude:: /examples/exceptions/override_default_handler.py
    :language: python


上面的代码将定义一个顶级异常处理程序，该处理程序将 ``plain_text_exception_handler`` 函数应用于所有继承自 ``HTTPException`` 的异常。当然，您可以更精细地控制：

.. literalinclude:: /examples/exceptions/per_exception_handlers.py
    :language: python


是使用内部具有切换逻辑的单个函数，还是使用多个函数，取决于您的具体需求。


异常处理层
^^^^^^^^^^^^^^^^^^^^^^^^^

由于 Litestar 允许用户以分层方式定义异常处理程序和中间件，即在单个路由处理程序、控制器、路由器或应用层上，因此需要多层异常处理程序来确保正确处理异常：


.. figure:: /images/exception-handlers.jpg
    :width: 400px

    异常处理程序


由于上述结构，ASGI 路由器本身引发的异常，即 ``404 Not Found`` 和 ``405 Method Not Allowed``，仅由应用层上定义的异常处理程序处理。因此，如果您想影响这些异常，则需要将它们的异常处理程序传递给 Litestar 构造函数，而不能为此目的使用其他层。

Litestar 支持在应用的所有层上定义异常处理程序，较低层覆盖其上层。在以下示例中，路由处理程序函数的异常处理程序将仅处理该路由处理程序内发生的 ``ValidationException``：

.. literalinclude:: /examples/exceptions/layered_handlers.py
    :language: python
