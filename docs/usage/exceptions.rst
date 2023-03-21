Exceptions and exception handling
=================================

Starlite define a base exception called :class:`StarliteException <starlite.exceptions.StarLiteException>` which serves
as a basis to all other exceptions.

In general, Starlite will raise two types of exceptions:

- Exceptions that arise during application init, which fall
- Exceptions that are raised as part of the normal application flow, i.e.
  exceptions in route handlers, dependencies and middleware, that should be serialized in some fashion.

Configuration Exceptions
------------------------

For missing extra dependencies, Starlite will raise either
:class:`MissingDependencyException <starlite.exceptions.MissingDependencyException>`. For example, if you try to use the
:doc:`SQLAlchemyPlugin </usage/plugins/sqlalchemy>` without having SQLAlchemy installed, this will be raised when you
start the application.

For other configuration issues, Starlite will raise
:class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>` with a message explaining the
issue.

Application Exceptions
----------------------

For application exceptions, Starlite uses the class :class:`HTTPException <.exceptions.http_exceptions.HTTPException>`,
which inherits from :class:`StarliteException <.exceptions.base.StarliteException>`. This exception will be serialized
into a JSON response of the following schema:

.. code-block:: json

   {
     "status_code": 500,
     "detail": "Internal Server Error",
     "extra": {}
   }

Starlite also offers several pre-configured exception subclasses with pre-set error codes that you can use, such as:


.. py:currentmodule:: starlite.exceptions.http_exceptions

+----------------------------------------+-------------+------------------------------------------+
| Exception                              | Status code | Description                              |
+========================================+=============+==========================================+
| :class:`ImproperlyConfiguredException` | 500         | Used internally for configuration errors |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ValidationException`           | 400         | Raised when validation or parsing failed |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotFoundException`             | 404         | HTTP status code 404                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`NotAuthorizedException`        | 401         | HTTP status code 401                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`PermissionDeniedException`     | 403         | HTTP status code 403                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`InternalServerException`       | 500         | HTTP status code 500                     |
+----------------------------------------+-------------+------------------------------------------+
| :class:`ServiceUnavailableException`   | 503         | HTTP status code 503                     |
+----------------------------------------+-------------+------------------------------------------+

When a value fails ``pydantic`` validation, the result will be a :class:`ValidationException` with the ``extra`` key set to the
pydantic validation errors. Thus, this data will be made available for the API consumers by default.


Exception handling
------------------

Starlite handles all errors by default by transforming them into **JSON responses**. If the errors are **instances of**
:class:`HTTPException`, the responses will include the appropriate ``status_code``.
Otherwise, the responses will default to ``500 - "Internal Server Error"``.

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

While it does not make much sense to have different functions with a top-level exception handling,
Starlite supports defining exception handlers on all layers of the app, with the lower layers overriding layer above
them. In the following example, the exception handler for the route handler function will only handle
the ``ValidationException`` occurring within that route handler:

.. literalinclude:: /examples/exceptions/layered_handlers.py
    :language: python


Exception handling layers
^^^^^^^^^^^^^^^^^^^^^^^^^

Since Starlite allows users to define both exception handlers and middlewares in a layered fashion, i.e. on individual
route handlers, controllers, routers or the app layer, multiple layers of exception handlers are required to ensure that
exceptions are handled correctly:


.. figure:: /images/exception-handlers.jpg
    :width: 400px

    Exception Handlers


As a result of the above structure, the exceptions raised by the ASGI Router itself, namely ``404 Not Found``
and ``405 Method Not Allowed`` are handled only by exception handlers defined on the app layer. Thus, if you want to affect
these exceptions, you will need to pass the exception handlers for them to the Starlite constructor and cannot use other
layers for this purpose.
