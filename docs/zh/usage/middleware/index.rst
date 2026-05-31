中间件
==========

Litestar 中的中间件是在应用程序入口点和路由处理函数之间"中间"调用的 ASGI 应用。

Litestar 附带了几个易于配置和使用的内置中间件。
有关更多详细信息，请参阅 :doc:`有关这些的文档 </usage/middleware/builtin-middleware>`。

.. seealso::

    如果您来自 Starlette / FastAPI，请查看迁移指南：

    * :ref:`迁移 - FastAPI/Starlette - 中间件 <migration/fastapi:Middleware>`


.. toctree::
    :titlesonly:

    using-middleware
    builtin-middleware
    creating-middleware
