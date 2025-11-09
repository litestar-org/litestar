Exceptions and exception handling
=================================

Litestar defines a base exception called :class:`LitestarException <litestar.exceptions.LitestarException>` which serves
as a base class for all other exceptions, see :mod:`API Reference <litestar.exceptions>`.

In general, Litestar has two scenarios for exception handling:

- Exceptions that are raised during application configuration, startup, and initialization, which are handled like regular Python exceptions
- Exceptions that are raised as part of the request handling, i.e.
  exceptions in route handlers, dependencies, and middleware, that should be returned as a response to the end user

Configuration Exceptions
------------------------

For missing extra dependencies, Litestar will raise either
:class:`MissingDependencyException <litestar.exceptions.MissingDependencyException>`. For example, if you try to use the
:ref:`SQLAlchemyPlugin <plugins>` without having SQLAlchemy installed, this will be raised when you
start the application.

For other configuration issues, Litestar will raise
:class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>` with a message explaining the
issue.

Application Exceptions
----------------------

For application exceptions, Litestar uses the class :class:`~litestar.exceptions.http_exceptions.HTTPException`,
which inherits from :class:`~litestar.exceptions.LitestarException`. This exception will be serialized
into a JSON response of the following schema:

.. code-block:: json

   {
     "status_code": 500,
     "detail": "Internal Server Error",
     "extra": {}
   }

Litestar also offers several pre-configured ``HTTPException`` subclasses with pre-set error codes that you can use, such as:


.. :currentmodule:: litestar.exceptions.http_exceptions

+----------------------------------------+-------------+------------------------------------------+
| Exception                              | Status code | Description                              |
+========================================+=============+==========================================+
| :class:`ImproperlyConfiguredException` | 500         | Used internally for configuration errors |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ValidationException`           | 400         | Raised when validation or parsing failed |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotAuthorizedException`        | 401         | HTTP status code 401                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`PermissionDeniedException`     | 403         | HTTP status code 403                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotFoundException`             | 404         | HTTP status code 404                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`InternalServerException`       | 500         | HTTP status code 500                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ServiceUnavailableException`   | 503         | HTTP status code 503                     |
+----------------------------------------+-------------+------------------------------------------+

.. :currentmodule:: None

When a value fails validation, the result will be a :class:`~litestar.exceptions.http_exceptions.ValidationException` with the ``extra`` key set to the validation error message.

.. warning:: All validation error messages will be made available for the API consumers by default.
    If this is not your intent, adjust the exception contents.


Exception handling
------------------

Litestar handles all errors by default by transforming them into **JSON responses**. If the errors are **instances of**
:class:`~litestar.exceptions.http_exceptions.HTTPException`, the responses will include the appropriate ``status_code``.
Otherwise, the responses will default to ``500 - "Internal Server Error"``.


The following handler for instance will default to ``MediaType.TEXT`` so the exception will be raised as text.

.. literalinclude:: /examples/exceptions/implicit_media_type.py
    :language: python

You can customize exception handling by passing a dictionary, mapping either status codes
or exception classes to callables. For example, if you would like to replace the default
exception handler with a handler that returns plain-text responses you could do this:

.. literalinclude:: /examples/exceptions/override_default_handler.py
    :language: python


The above will define a top level exception handler that will apply the ``plain_text_exception_handler`` function to all
exceptions that inherit from ``HTTPException``. You could of course be more granular:

.. literalinclude:: /examples/exceptions/per_exception_handlers.py
    :language: python


The choice whether to use a single function that has switching logic inside it, or multiple functions depends on your
specific needs.


Exception handling layers
^^^^^^^^^^^^^^^^^^^^^^^^^

Since Litestar allows users to define both exception handlers and middlewares in a layered fashion, i.e. on individual
route handlers, controllers, routers, or the app layer, multiple layers of exception handlers are required to ensure that
exceptions are handled correctly:


.. figure:: /images/exception-handlers.jpg
    :width: 400px

    Exception Handlers


As a result of the above structure, the exceptions raised by the ASGI Router itself, namely ``404 Not Found``
and ``405 Method Not Allowed`` are handled only by exception handlers defined on the app layer. Thus, if you want to affect
these exceptions, you will need to pass the exception handlers for them to the Litestar constructor and cannot use other
layers for this purpose.

Litestar supports defining exception handlers on all layers of the app, with the lower layers overriding layer above
them. In the following example, the exception handler for the route handler function will only handle
the ``ValidationException`` occurring within that route handler:

.. literalinclude:: /examples/exceptions/layered_handlers.py
    :language: python
