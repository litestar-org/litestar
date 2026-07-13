Responses
=========

Litestar allows for several ways in which HTTP responses can be specified and handled, each fitting a different use
case. The base pattern though is straightforward - simply return a value from a route handler function and let
Litestar take care of the rest:

.. code-block:: python

   from pydantic import BaseModel
   from litestar import get


   class Resource(BaseModel):
       id: int
       name: str


   @get("/resources")
   def retrieve_resource() -> Resource:
       return Resource(id=1, name="my resource")

In the example above, the route handler function returns an instance of the ``Resource`` pydantic class. This value will
then be used by Litestar to construct an instance of the :class:`Response <litestar.response.Response>`
class using defaults values: the response status code will be set to ``200`` and it's ``Content-Type`` header will be set
to ``application/json``. The ``Resource`` instance will be serialized into JSON and set as the response body.


Contents
--------

* :doc:`media_types_and_status_codes` covers configuring response media types and status codes.
* :doc:`returning_responses` covers returning data in specific formats, content negotiation, response instances, and
  redirects.
* :doc:`headers_and_cookies` covers setting response headers and cookies, including dynamic configuration and predefined
  headers.
* :doc:`special_responses` covers file, streaming, server-sent event, template, and custom responses.
* :doc:`advanced_topics` covers background tasks and pagination.


.. toctree::
    :titlesonly:

    media_types_and_status_codes
    returning_responses
    headers_and_cookies
    special_responses
    advanced_topics
