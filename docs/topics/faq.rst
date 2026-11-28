FAQ
===

This page collects short answers to questions that come up again and again in the
Litestar community. Every entry is a recipe: the problem people run into, and the
smallest change that fixes it.

If a question is missing, bring it up on the
`Discord help forum <https://discord.gg/litestar>`_ or open an issue. This section is
meant to grow whenever the same thing is asked twice.


Why don't I see a stack trace when a route handler raises an exception?
-----------------------------------------------------------------------

Because by default Litestar neither returns the traceback to the client *nor* writes it
to the logs. Both are controlled by ``debug`` and by ``log_exceptions`` on the logging
configuration:

.. list-table::
    :header-rows: 1

    * - Configuration
      - Traceback in response
      - Traceback in logs
    * - ``debug=False`` (the default)
      - no
      - no
    * - ``debug=True``
      - yes
      - yes
    * - ``debug=False`` and ``LoggingConfig(log_exceptions="always")``
      - no
      - yes
    * - ``debug=False`` and ``LoggingConfig(log_exceptions="never")``
      - no
      - no

``log_exceptions`` defaults to ``"debug"``, which means *log exceptions when*
``app.debug is True``. An exception raised in a route handler on a default production
application therefore disappears completely from both the response and the logs, which
is usually why it looks like there is no stack trace at all.


Getting the traceback in the response
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set ``debug=True`` while developing:

.. code-block:: python

    from litestar import Litestar, get


    @get("/")
    def handler() -> None:
        raise RuntimeError("something went wrong")


    app = Litestar(route_handlers=[handler], debug=True)

A ``500`` response now contains the full traceback, rendered as HTML for browsers and as
plain text for everything else. If you run the app from the CLI, the same is available
via the ``--debug`` flag::

    litestar run --debug

Or via an environment variable::

    LITESTAR_DEBUG=1 litestar run

.. warning::

    ``debug=True`` exposes source code and configuration details to anyone who can reach
    the application. It must never be enabled in production.


Logging the traceback without exposing it
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Keep ``debug=False`` and tell Litestar to always log exceptions:

.. code-block:: python

    from litestar import Litestar
    from litestar.logging import LoggingConfig

    app = Litestar(
        route_handlers=[...],
        logging_config=LoggingConfig(log_exceptions="always"),
    )

The traceback is written to the ``litestar`` logger while clients keep receiving the
plain ``{"status_code": 500, "detail": "Internal Server Error"}`` body::

    ERROR - ... - litestar - Uncaught exception (connection_type=http, path='/boom'):
    Traceback (most recent call last):
      ...
    RuntimeError: something went wrong

If you provide your own logging configuration, make sure the ``litestar`` logger is not
disabled and that its level is not raised above ``ERROR``, otherwise the traceback is
filtered out again.

``LoggingConfig(log_exceptions="never")`` turns exception logging off entirely, and
``disable_stack_trace={404, NotAuthorizedException}`` suppresses tracebacks for specific
status codes or exception types.


Watching out for custom exception handlers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A handler you register yourself replaces the built-in one, and the debug response is
never used:

.. code-block:: python

    from litestar import Litestar, Request, Response


    def handle_error(request: Request, exc: Exception) -> Response:
        return Response(content={"detail": "oops"}, status_code=500)


    app = Litestar(route_handlers=[...], exception_handlers={Exception: handle_error})

The traceback is still logged while ``debug=True``, or when
``log_exceptions="always"``, but it will not be part of the response because your handler
decides what the response looks like. If you want to keep the traceback visible in that
case, log the exception from inside the handler.

.. seealso::

    :doc:`/usage/exceptions`
        How the built-in exception handlers and custom handlers interact.

    :doc:`/usage/debugging`
        Attaching a debugger and dropping into ``pdb`` when an exception occurs.

    :doc:`/usage/logging`
        Configuring the ``litestar`` logger, formatters and handlers.
