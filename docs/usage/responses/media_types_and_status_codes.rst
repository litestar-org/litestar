Media Types and Status Codes
============================

Media Type
----------

You do not have to specify the ``media_type`` kwarg in the route handler function if the response should be JSON. But
if you wish to return a response other than JSON, you should specify this value. You can use
the :class:`MediaType <litestar.enums.MediaType>` enum for this purpose:

.. code-block:: python

   from litestar import MediaType, get


   @get("/resources", media_type=MediaType.TEXT)
   def retrieve_resource() -> str:
       return "The rumbling rabbit ran around the rock"

The value of the ``media_type`` kwarg affects both the serialization of response data and the generation of OpenAPI docs.
The above example will cause Litestar to serialize the response as a simple bytes string with a ``Content-Type`` header
value of ``text/plain``. It will also set the corresponding values in the OpenAPI documentation.

MediaType has the following members:


* MediaType.JSON: ``application/json``
* MediaType.MessagePack: ``application/x-msgpack``
* MediaType.TEXT: ``text/plain``
* MediaType.HTML: ``text/html``

You can also set any `IANA referenced <https://www.iana.org/assignments/media-types/media-types.xhtml>`_ media type
string as the ``media_type``. While this will still affect the OpenAPI generation as expected, you might need to handle
serialization using either a :ref:`custom response <usage/responses/special_responses:Custom Responses>` with serializer or by serializing
the value in the route handler function.


Status Codes
------------

You can control the response ``status_code`` by setting the corresponding kwarg to the desired value:

.. code-block:: python

   from pydantic import BaseModel
   from litestar import get
   from litestar.status_codes import HTTP_202_ACCEPTED


   class Resource(BaseModel):
       id: int
       name: str


   @get("/resources", status_code=HTTP_202_ACCEPTED)
   def retrieve_resource() -> Resource:
       return Resource(id=1, name="my resource")

If ``status_code`` is not set by the user, the following defaults are used:


* POST: 201 (Created)
* DELETE: 204 (No Content)
* GET, PATCH, PUT: 200 (Ok)

.. attention::

    For status codes < 100 or 204, 304 statuses, no response body is allowed. If you specify a return annotation other
    than ``None``, an :class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>` will be raised.

.. note::

    When using the ``route`` decorator with multiple http methods, the default status code is ``200``.
    The default for ``delete`` is ``204`` because by default it is assumed that delete operations return no data.
    This though might not be the case in your implementation - so take care of setting it as you see fit.

.. tip::

   While you can write integers as the value for ``status_code``, e.g. ``200``, it's best practice to use constants (also in
   tests). Litestar includes easy to use statuses that are exported from ``litestar.status_codes``, e.g. ``HTTP_200_OK``
   and ``HTTP_201_CREATED``. Another option is the :class:`http.HTTPStatus` enum from the standard library, which also offers
   extra functionality.
