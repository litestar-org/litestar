Logging
=======

Application and request level loggers can be configured using the :class:`~litestar.logging.config.LoggingConfig`:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.logging import LoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = LoggingConfig(
       loggers={
           "my_app": {
               "level": "INFO",
               "handlers": ["queue_listener"],
           }
       }
   )

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

.. attention::

    Litestar configures a non-blocking ``QueueListenerHandler`` which
    is keyed as ``queue_listener`` in the logging configuration. The above example is using this handler,
    which is optimal for async applications. Make sure to use it in your own loggers as in the above example.



Standard Library Logging
^^^^^^^^^^^^^^^^^^^^^^^^

`logging <https://docs.python.org/3/howto/logging.html>`_ is Python's builtin standard logging library. Works with gunicorn and uvicorn as well.

.. code-block:: python

    from litestar import Litestar, Request, get
    import logging


    def get_logger(module_name: str) -> logging.Logger:
        """Return logger object."""
        # create logger
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)
        return logger


    logger = get_logger(__name__)


    @get("/")
    def my_router_handler(self, request: Request) -> None:
        logger.info("inside a request")
        return None


    app = Litestar(route_handlers=[my_router_handler])



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
