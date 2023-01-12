=======
Logging
=======

Starlite has builtin Pydantic-based logging support which allows users to easily define
logging configurations. Following is an example showcasing that feature:

.. code-block:: python

    from starlite import Starlite, LoggingConfig, Request, get


    @get("/")
    def my_route_handler(request: Request) -> None:
        request.logger.info("inside a request")


    logging_config = LoggingConfig(
        loggers={
            "my_app": {
                "level": "INFO",
                "handlers": ["queue_listener"],
            }
        }
    )

    app = Starlite(route_handlers=[my_route_handler], logging_config=logging_config)

.. important::

   Starlite configures a non-blocking ``QueueListenerHandler`` which is keyed as
   ``queue_listener`` in the logging configuration. The above example is using this
   handler which is optimal for asynchronous applications. So, make sure to use it in
   your own loggers as suggested in the example above.

Using Picologging
=================

`Picologging <https://microsoft.github.io/picologging>`_ is a high performance logging
library developed by Microsoft. Starlite will by default use this library if installed,
requiring zero-config from the user-end. Hence, if ``picologging`` is added as an extra
dependency, the example above will work as-is!

Using StructLog
===============

`StructLog <https://www.structlog.org>`_ is a powerful structured-logging library.
Starlite ships with a dedicated logging config for using it as follows:

.. code-block:: python

    from starlite import Starlite, StructLoggingConfig, Request, get


    @get("/")
    def my_route_handler(request: Request) -> None:
        request.logger.info("inside a request")


    logging_config = StructLoggingConfig()

    app = Starlite(route_handlers=[my_route_handler], logging_config=logging_config)

Subclass Logging Configs
========================

Its also possible to create your own custom ``LoggingConfig`` clas. You can do so by
subclassing the |BaseLoggingConfig|_ class & implementing the ``configure`` method.

.. TODO: Add an example code snippet to show how its done.

.. |BaseLoggingConfig| replace:: ``BaseLoggingConfig``
.. _BaseLoggingConfig: ./reference/config/8-logging-config/#starlite.config.logging.BaseLoggingConfig
