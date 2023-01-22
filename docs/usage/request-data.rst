Request data
============

Request body
------------

The body of HTTP requests can be accessed using the special ``data`` parameter in a handler function.

.. literalinclude:: /examples/request_data/request_data_1.py
    :language: python



The type of ``data`` an be any supported type, including


* :func:`dataclasses <dataclasses.dataclass>`
* :class:`TypedDicts <typing.TypedDict>`
* Pydantic models
* Arbitrary stdlib types
* Typed supported via :doc:`plugins </usage/plugins/index>`

.. literalinclude:: /examples/request_data/request_data_2.py
    :language: python



Validation and customizing OpenAPI documentation
------------------------------------------------

With the help of :class:`Body <starlite.params.Body>`, you have fine-grained control over the validation
of the request body, and can also customize the OpenAPI documentation:

.. literalinclude:: /examples/request_data/request_data_3.py
    :language: python



Specifying a content-type
-------------------------

By default, Starlite will try to parse the request body as JSON. While this may be desired
in most cases, you might want to specify a different type. You can do so by passing a
:class:`RequestEncodingType <starlite.enums.RequestEncodingType>` to ``Body``. This will also
help to generate the correct media-type in the OpenAPI schema.

URL Encoded Form Data
^^^^^^^^^^^^^^^^^^^^^

To access data sent as `url-encoded form data <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_,
i.e. ``application/x-www-form-urlencoded`` Content-Type header, use :class:`Body <starlite.params.Body>` and specify
:class:`RequestEncodingType.URL_ENCODED <starlite.enums.RequestEncodingType>` as the ``media_type``:

.. literalinclude:: /examples/request_data/request_data_4.py
    :language: python

.. note::

    URL encoded data is inherently less versatile than JSON data - for example, it cannot handle complex
    dictionaries and deeply nested data. It should only be used for simple data structures.


MultiPart Form Data
^^^^^^^^^^^^^^^^^^^

You can access data uploaded using a request with a
`multipart/form-data <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST>`_
Content-Type header by specifying it in the :class:`Body <starlite.params.Body>` function:

.. literalinclude:: /examples/request_data/request_data_5.py
    :language: python



File uploads
------------

In case of files uploaded, Starlite transforms the results into an instance
of :class:`UploadFile <.datastructures.upload_file.UploadFile>` class, which offer a convenient
interface for working with files. Therefore, you need to type your file uploads accordingly.

To access a single file simply type ``data`` as :class:`UploadFile <.datastructures.upload_file.UploadFile>`:


.. tab-set::

    .. tab-item:: Async

        .. literalinclude:: /examples/request_data/request_data_6.py
            :language: python

    .. tab-item:: Sync

        .. literalinclude:: /examples/request_data/request_data_7.py
            :language: python

.. admonition:: Technical details
    :class: info

    :class:`UploadFile <.datastructures.UploadFile>` wraps
    :class:`SpooledTemporaryFile <tempfile.SpooledTemporaryFile>` so it can be used asynchronously. Inside of a
    synchronous function we don't need this wrapper, so we can use
    :meth:`SpooledTemporaryFile.read <tempfile.SpooledTemporaryFile.read>` directly.



Multiple files
^^^^^^^^^^^^^^

To access multiple files with known filenames, you can use a pydantic model:

.. literalinclude:: /examples/request_data/request_data_8.py
    :language: python



Files as a dictionary
^^^^^^^^^^^^^^^^^^^^^

If you do not care about parsing and validation and only want to access the form data as a dictionary, you can use a ``dict`` instead:

.. literalinclude:: /examples/request_data/request_data_9.py
    :language: python



Files as a list
^^^^^^^^^^^^^^^

Finally, you can also access the files as a list without the filenames:

.. literalinclude:: /examples/request_data/request_data_10.py
    :language: python


MessagePack data
----------------

To receive `MessagePack <https://msgpack.org/>`_ data, specify the appropriate ``Content-Type``
for ``Body`` , by using :class:`RequestEncodingType.MESSAGEPACK <.enums.RequestEncodingType>`:

.. literalinclude:: /examples/request_data/msgpack_request.py
   :caption: msgpack_request.py
   :language: python
