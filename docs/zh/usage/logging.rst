.. _logging-usage:

日志记录
=======

可以使用 :class:`~litestar.logging.config.LoggingConfig` 配置应用程序和请求级别的日志记录器：

.. code-block:: python

   import logging

   from litestar import Litestar, Request, get
   from litestar.logging import LoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("在请求内部")
       return None


   logging_config = LoggingConfig(
       root={"level": "INFO", "handlers": ["queue_listener"]},
       formatters={
           "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
       },
       log_exceptions="always",
   )

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

.. attention::

    Litestar 配置了一个非阻塞的 ``QueueListenerHandler``，它在日志配置中键为 ``queue_listener``。上面的示例使用此处理程序，它对于异步应用程序是最佳的。请确保在您自己的日志记录器中使用它，如上例所示。

.. attention::

    默认情况下不会记录异常，调试模式除外。如果需要，请确保使用 ``log_exceptions="always"`` 来记录异常，如上例所示。

控制异常日志记录
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

虽然 ``log_exceptions`` 控制何时记录异常，但有时您可能希望抑制特定异常类型或 HTTP 状态码的堆栈跟踪。``disable_stack_trace`` 参数允许您指定一组不应在日志中生成堆栈跟踪的异常类型或状态码：

.. code-block:: python

   from litestar import Litestar
   from litestar.logging import LoggingConfig

   # 不为 404 错误和 ValueError 异常记录堆栈跟踪
   logging_config = LoggingConfig(
       debug=True,
       disable_stack_trace={404, ValueError},
   )

   app = Litestar(logging_config=logging_config)

这对于您在正常操作中预期的常见异常特别有用，不需要详细的堆栈跟踪。

使用 Python 标准库
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`logging <https://docs.python.org/3/howto/logging.html>`_ 是 Python 的内置标准日志库，可以通过 ``LoggingConfig`` 进行配置。

``LoggingConfig.configure()`` 方法返回对 ``logging.getLogger`` 的引用，可用于访问日志记录器实例。因此，可以使用 ``logging_config.configure()()`` 检索根日志记录器，如下例所示：

.. code-block:: python

    import logging

    from litestar import Litestar, Request, get
    from litestar.logging import LoggingConfig

    logging_config = LoggingConfig(
        root={"level": "INFO", "handlers": ["queue_listener"]},
        formatters={
            "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
        },
        log_exceptions="always",
    )

    logger = logging_config.configure()()


    @get("/")
    def my_router_handler(request: Request) -> None:
        request.logger.info("在请求内部")
        logger.info("这里也是")


    app = Litestar(
        route_handlers=[my_router_handler],
        logging_config=logging_config,
    )

上面的示例与不使用 litestar ``LoggingConfig`` 而使用 logging 相同。

.. code-block:: python

    import logging

    from litestar import Litestar, Request, get
    from litestar.logging.config import LoggingConfig


    def get_logger(mod_name: str) -> logging.Logger:
        """返回日志记录器对象。"""
        format = "%(asctime)s: %(name)s: %(levelname)s: %(message)s"
        logger = logging.getLogger(mod_name)
        # 写入 stdout
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(format))
        logger.addHandler(ch)
        return logger


    logger = get_logger(__name__)


    @get("/")
    def my_router_handler(request: Request) -> None:
        logger.info("请求内的日志记录器")


    app = Litestar(
        route_handlers=[my_router_handler],
    )


使用 Picologging
^^^^^^^^^^^^^^^^^

`Picologging <https://github.com/microsoft/picologging>`_ 是由 Microsoft 开发的高性能日志库。如果安装了此库，Litestar 将自动默认使用它 - 用户无需进行任何配置。也就是说，如果存在 ``picologging``，前面的示例将自动使用它。

使用 StructLog
^^^^^^^^^^^^^^^

`StructLog <https://www.structlog.org/en/stable/>`_ 是一个强大的结构化日志库。Litestar 附带了专用的日志插件和配置来使用它：

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.plugins.structlog import StructlogPlugin


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("在请求内部")
       return None


   structlog_plugin = StructlogPlugin()

   app = Litestar(route_handlers=[my_router_handler], plugins=[StructlogPlugin()])

子类化日志配置
^^^^^^^^^^^^^^^^^^^^^^^^

您可以通过子类化 :class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>` 并实现 ``configure`` 方法来轻松创建自己的 ``LoggingConfig`` 类。
