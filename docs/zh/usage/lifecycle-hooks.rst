生命周期钩子
================

生命周期钩子允许在请求-响应周期的某个时刻执行可调用对象。可用的钩子有：

+--------------------------------------+------------------------------------+
| 名称                                 | 运行时机                           |
+======================================+====================================+
| `before_request`_                    | 在路由器处理函数之前               |
+--------------------------------------+------------------------------------+
| `after_request`_                     | 在路由处理函数之后                 |
+--------------------------------------+------------------------------------+
| `after_response`_                    | 在响应发送之后                     |
+--------------------------------------+------------------------------------+

.. _before_request:

请求前
--------------

``before_request`` 钩子在调用路由处理函数之前立即运行。它可以是接受 :class:`~litestar.connection.Request` 作为其第一个参数并返回 ``None`` 或可在响应中使用的值的任何可调用对象。如果返回值，则将绕过此请求的路由器处理程序。

.. literalinclude:: /examples/lifecycle_hooks/before_request.py
    :language: python


.. _after_request:

请求后
-------------

生命周期钩子
================

生命周期钩子允许在请求-响应周期的某个时刻执行可调用对象。可用的钩子有:

+--------------------------------------+------------------------------------+
| 名称                                 | 运行时机                           |
+======================================+====================================+
| `before_request`_                    | 在路由处理函数之前                 |
+--------------------------------------+------------------------------------+
| `after_request`_                     | 在路由处理函数之后                 |
+--------------------------------------+------------------------------------+
| `after_response`_                    | 在响应发送之后                     |
+--------------------------------------+------------------------------------+

.. _before_request:

请求前
--------------

``before_request`` 钩子在调用路由处理函数之前立即运行。它可以是任何接受 :class:`~litestar.connection.Request` 作为其第一个参数的可调用对象,并返回 ``None`` 或可以在响应中使用的值。如果返回了值,则将绕过此请求的路由处理程序。

.. literalinclude:: /examples/lifecycle_hooks/before_request.py
    :language: python


.. _after_request:

请求后
-------------

``after_request`` 钩子在路由处理程序返回并解析响应对象后运行。它可以是任何接受 :class:`~litestar.response.Response` 实例作为其第一个参数并返回 ``Response`` 实例的可调用对象。返回的 ``Response`` 实例不一定必须是接收到的实例。

.. literalinclude:: /examples/lifecycle_hooks/after_request.py
    :language: python


.. _after_response:

响应后
--------------

``after_response`` 钩子在服务器返回响应后运行。它可以是接受 :class:`~litestar.connection.Request` 作为其第一个参数并且不返回任何值的任何可调用对象。

此钩子用于数据后处理、向第三方服务传输数据、收集指标等。

.. literalinclude:: /examples/lifecycle_hooks/after_response.py
    :language: python


.. note::

    由于在调用 ``after_response`` 时请求已经返回,因此 ``COUNTER`` 的更新状态不会反映在响应中。


分层钩子
-------------

.. admonition:: 分层架构

    生命周期钩子是 Litestar 分层架构的一部分,这意味着你可以在应用程序的每一层上设置它们。如果你在多个层上设置钩子,最接近路由处理程序的层将优先。

    你可以在此处阅读更多相关信息:
    :ref:`分层架构 <usage/applications:layered architecture>`


.. literalinclude:: /examples/lifecycle_hooks/layered_hooks.py
   :language: python
