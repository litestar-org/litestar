Logging
=======

Starlite supports builtin logging configurations using `Pydantic <https://pydantic.dev>`_. Here is how its easily
possible to define custom logging functionalities:

.. code-block:: python

    from starlite import Starlite, LoggingConfig, Request, get


    @get("/")
    def my_router_handler(request: Request) -> None:
        request.logger.info("inside a request")
        return None


    logging_config = LoggingConfig(
        loggers={
            "my_app": {
                "level": "INFO",
                "handlers": ["queue_listener"],
            },
        },
    )

    app = Starlite(route_handlers=[my_router_handler], logging_config=logging_config)

.. attention::

   Starlite configures a non-blocking :class:`QueueListenerHandler <>` which is keyed as ``queue_listener`` in the
   logging configuration. The example above is using this handler which is optimal for async applications. So be sure
   to use it in your customised loggers as suggested in the example above.

Using Picologging
-----------------

Any Starlite application can also use the high performance `Picologging <https://microsoft.github.io/picologging>`_
library built by Microsoft. If already installed, Starlite will instead default to using this library automatically
requiring no configuration on part of the user. In other words, the example shared above in the previous section of this
document will work without any flaws.

Using StructLog
---------------

`StructLog <https://www.structlog.org>`_ is another powerful structured logging library which Starlite supports a
dedicated logging configuration for. And here is how you can configure it:

.. code-block:: python

   from starlite import Starlite, StructLoggingConfig, Request, get


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = StructLoggingConfig()

   app = Starlite(route_handlers=[my_router_handler], logging_config=logging_config)

Subclass Logging Configs
------------------------

If none of the aforementioned logging configuration suit your needs, Starlite enables the user to create customised
logging configurations as well. This is done by creating a custom
:class:`LoggingConfig <starlite.config.logging.LoggingConfig>` class and subclassing it on the
:class:`BaseLoggingConfig <starlite.config.logging.BaseLoggingConfig>` class to implement the ``configure`` method.

.. TODO: Example(s)?
