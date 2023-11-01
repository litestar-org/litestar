Logging
=======

Application and request level loggers can be configured using the :class:`~litestar.logging.config.LoggingConfig`:

.. code-block:: python

   import logging

   from litestar import Litestar, Request, get
   from litestar.logging import LoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = LoggingConfig(
       loggers={
           "root": {"level": logging.getLevelName(logging.INFO), "handlers": ["console"]},
           "my_app": {
               "level": "INFO",
               "handlers": ["queue_listener"],
           },
       }
   )

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

.. attention::

    Litestar configures a non-blocking ``QueueListenerHandler`` which
    is keyed as ``queue_listener`` in the logging configuration. The above example is using this handler,
    which is optimal for async applications. Make sure to use it in your own loggers as in the above example.



Standard Library Logging (Manual Configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`logging <https://docs.python.org/3/howto/logging.html>`_ is Python's builtin standard logging library and can be integrated with `LoggingConfig` as the `root` logging.

.. code-block:: python

    import logging

    from litestar import Litestar, Request, get
    from litestar.logging.config import LoggingConfig

    log_config = LoggingConfig(
        root={"level": logging.getLevelName(logging.INFO), "handlers": ["console"]},
        formatters={
            "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
        },
    )

    logger = log_config.configure()()


    @get("/")
    def my_router_handler(request: Request) -> None:
        request.logger.info("inside a request")
        logger.info("here too")


    app = Litestar(
        route_handlers=[my_router_handler],
        logging_config=log_config,
    )

The above example is the same as using logging without the litestar LoggingConfig.

.. code-block:: python
    import logging

    from litestar import Litestar, Request, get
    from litestar.logging.config import LoggingConfig


    def get_logger(mod_name: str) -> logging.Logger:
        """Return logger object."""
        format = "%(asctime)s: %(name)s: %(levelname)s: %(message)s"
        logger = logging.getLogger(mod_name)
        # Writes to stdout
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(format))
        logger.addHandler(ch)
        return logger


    logger = get_logger(__name__)


    @get("/")
    def my_router_handler(request: Request) -> None:
        logger.info("logger inside a request")


    app = Litestar(
        route_handlers=[my_router_handler],
    )


Using Picologging
^^^^^^^^^^^^^^^^^

`Picologging <https://github.com/microsoft/picologging>`_ is a high performance logging library that is developed by
Microsoft. Litestar will default to using this library automatically if its installed - requiring zero configuration on
the part of the user. That is, if ``picologging`` is present the previous example will work with it automatically.

Using StructLog
^^^^^^^^^^^^^^^

`StructLog <https://www.structlog.org/en/stable/>`_ is a powerful structured-logging library. Litestar ships with a dedicated
logging config for using it:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.logging import StructLoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = StructLoggingConfig()

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

Subclass Logging Configs
^^^^^^^^^^^^^^^^^^^^^^^^

You can easily create you own ``LoggingConfig`` class by subclassing
:class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>` and implementing the ``configure`` method.
