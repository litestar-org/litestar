===============
Problem Details
===============

.. versionadded:: 2.9.0

Problem details are a standardized way of providing machine-readable details of errors in HTTP
responses as specified in `RFC 9457`_, the latest RFC at the time of writing.

.. _RFC 9457: https://datatracker.ietf.org/doc/html/rfc9457

Usage
-----

To send a problem details response, the ``ProblemDetailsPlugin`` should be registered and then
a ``ProblemDetailsException`` can be raised anywhere which will automatically be converted
into a problem details response.

.. literalinclude:: /examples/plugins/problem_details/basic_usage.py
    :language: python
    :caption: Basic usage of the problem details plugin.

You can convert all ``HTTPExceptions`` into problem details response by enabling the flag in the ``ProblemDetailsConfig.``

.. literalinclude:: /examples/plugins/problem_details/convert_http_exceptions.py
    :language: python
    :caption: Converting ``HTTPException`` into problem details response.


You can also convert any exception that is not a ``HTTPException`` into a problem details response
by providing a mapping of the exception type to a callable that converts the exception into a
``ProblemDetailsException.``

.. tip:: This can be used to override how the ``HTTPException`` is converted into a problem details response as well.

.. literalinclude:: /examples/plugins/problem_details/convert_exceptions.py
    :language: python
    :caption: Converting custom exceptions into problem details response.

.. warning:: If the ``extra`` field is a ``Mapping``, then it's merged into the problem details response, otherwise it's included in the response with the key ``extra``.
