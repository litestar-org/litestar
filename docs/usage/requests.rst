Requests
========

Request body
------------

The body of HTTP requests can be accessed using the special ``data`` parameter in a handler function.

.. literalinclude:: /examples/request_data/request_data_1.py
    :language: python


The type of ``data`` can be any supported type, including


* Arbitrary stdlib types
* :class:`TypedDicts <typing.TypedDict>`
* :func:`dataclasses <dataclasses.dataclass>`
* Types supported via :doc:`plugins </usage/plugins/index>` ie.
    - `Msgspec Struct <https://jcristharif.com/msgspec/structs.html>`_
    - `Pydantic models <https://docs.pydantic.dev/usage/models/>`_
    - `Attrs classes <https://www.attrs.org/en/stable/>`_


.. literalinclude:: /examples/request_data/request_data_2.py
    :language: python


Validation and customization of OpenAPI documentation
-----------------------------------------------------

With the help of :class:`Body <litestar.params.Body>`, you have fine-grained control over the validation
of the request body, and can also customize the OpenAPI documentation:


.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_3.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 35-41


Content-type
------------

By default, Litestar will try to parse the request body as JSON. While this may be desired
in most cases, you might want to specify a different type. You can do so by passing a
:class:`RequestEncodingType <litestar.enums.RequestEncodingType>` to ``Body``. This will also
help to generate the correct media-type in the OpenAPI schema.

URL Encoded Form Data
^^^^^^^^^^^^^^^^^^^^^

To access data sent as `url-encoded form data <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_,
i.e. ``application/x-www-form-urlencoded`` Content-Type header, use :class:`Body <litestar.params.Body>` and specify
:class:`RequestEncodingType.URL_ENCODED <litestar.enums.RequestEncodingType>` as the ``media_type``:

.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_4.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 44-48

.. note::

    URL encoded data is inherently less versatile than JSON data - for example, it cannot handle complex
    dictionaries and deeply nested data. It should only be used for simple data structures.


MultiPart Form Data
^^^^^^^^^^^^^^^^^^^

You can access data uploaded using a request with a
`multipart/form-data <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_
Content-Type header by specifying it in the :class:`Body <litestar.params.Body>` function:

.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_5.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 51-64


File uploads
------------

In case of files uploaded, Litestar transforms the results into an instance
of :class:`UploadFile <.datastructures.upload_file.UploadFile>` class, which offer a convenient
interface for working with files. Therefore, you need to type your file uploads accordingly.

To access a single file simply type ``data`` as :class:`UploadFile <.datastructures.upload_file.UploadFile>`:


.. tab-set::

    .. tab-item:: Async

        .. tab-set::

            .. tab-item:: example

                .. literalinclude:: /examples/request_data/request_data_6.py
                    :language: python

            .. tab-item:: how to test

                .. literalinclude:: ../../tests/examples/test_request_data.py
                    :language: python
                    :lines: 67-71

    .. tab-item:: Sync

        .. tab-set::

            .. tab-item:: example

                .. literalinclude:: /examples/request_data/request_data_7.py
                    :language: python

            .. tab-item:: how to test

                .. literalinclude:: ../../tests/examples/test_request_data.py
                    :language: python
                    :lines: 74-78

.. admonition:: Technical details
    :class: info

    :class:`UploadFile <.datastructures.UploadFile>` wraps
    :class:`SpooledTemporaryFile <tempfile.SpooledTemporaryFile>` so it can be used asynchronously. Inside a synchronous
    function we don't need this wrapper, so we can use its :meth:`read <io.TextIOBase.read>` method directly.



Multiple files
^^^^^^^^^^^^^^

To access multiple files with known filenames, you can use a pydantic model:


.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_8.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 81-87


Files as a dictionary
^^^^^^^^^^^^^^^^^^^^^

If you do not care about parsing and validation and only want to access the form data as a dictionary, you can use a ``dict`` instead:

.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_9.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 90-97


Files as a list
^^^^^^^^^^^^^^^

Finally, you can also access the files as a list without the filenames:

.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/request_data_10.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 100-133

MessagePack data
----------------

To receive `MessagePack <https://msgpack.org/>`_ data, specify the appropriate ``Content-Type``
for ``Body``\ , by using :class:`RequestEncodingType.MESSAGEPACK <.enums.RequestEncodingType>`:

.. tab-set::

    .. tab-item:: example

        .. literalinclude:: /examples/request_data/msgpack_request.py
            :language: python

    .. tab-item:: how to test

        .. literalinclude:: ../../tests/examples/test_request_data.py
            :language: python
            :lines: 136-141

Custom Request
--------------

.. versionadded:: 2.7.0

Litestar supports custom ``request_class`` instances, which can be used to further configure the default :class:`Request`.
The example below illustrates how to implement custom request class for the whole application.

.. dropdown:: Example of a custom request at the application level

    .. tab-set::

        .. tab-item:: example

            .. literalinclude:: /examples/request_data/custom_request.py
                :language: python

        .. tab-item:: how to test

            .. literalinclude:: ../../tests/examples/test_request_data.py
                :language: python
                :lines: 144-147

.. admonition:: Layered architecture

   Request classes are part of Litestar's layered architecture, which means you can
   set a request class on every layer of the application. If you have set a request
   class on multiple layers, the layer closest to the route handler will take precedence.

   You can read more about this in the :ref:`usage/applications:layered architecture` section


Limits
-------

Body size
^^^^^^^^^^

A limit for the allowed request body size can be set on all layers via the
``request_max_body_size`` parameter and defaults to 10MB. If a request body exceeds this
limit, a ``413 - Request Entity Too Large``
response will be returned. This limit applies to all methods of consuming the request
body, including requesting it via the ``body`` parameter in a route handler and
consuming it through a manually constructed :class:`~litestar.connection.Request`
instance, e.g. in a middleware.

To disable this limit for a specific handler / router / controller, it can be set to
:obj:`None`.

.. danger::
    Setting ``request_max_body_size=None`` is strongly discouraged as it exposes the
    application to a denial of service (DoS) attack by sending arbitrarily large
    request bodies to the affected endpoint. Because Litestar has to read the whole body
    to perform certain actions, such as parsing JSON, it will fill up all the available
    memory / swap until the application / server crashes, should no outside limits be
    imposed.

    This is generally only recommended in environments where the application is running
    behind a reverse proxy such as NGINX, where a size limit is already set.


.. danger::
    Since ``request_max_body_size`` is handled on a per-request basis, it won't affect
    middlewares or ASGI handlers when they try to access the request body via the raw
    ASGI events. To avoid this, middlewares and ASGI handlers should construct a
    :class:`~litestar.connection.Request` instance and use the regular
    :meth:`~litestar.connection.Request.stream` /
    :meth:`~litestar.connection.Request.body` or content-appropriate method to consume
    the request body in a safe manner.


.. tip::
    For requests that define a ``Content-Length`` header, Litestar will not attempt to
    read the request body should the header value exceed the ``request_max_body_size``.

    If the header value is within the allowed bounds, Litestar will verify during the
    streaming of the request body that it does not exceed the size specified in the
    header. Should the request exceed this size, it will abort the request with a
    ``400 - Bad Request``.
