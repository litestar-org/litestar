Headers and Cookies
===================

Setting Response Headers
-------------------------

Litestar allows you to define response headers by using the ``response_headers`` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers, and the app
itself:

.. literalinclude:: /examples/responses/response_headers_1.py
    :language: python


In the above example the response returned from ``my_route_handler`` will have headers set from each layer of the
application using the given key+value combinations. I.e. it will be a dictionary equal to this:

.. code-block:: json

   {
     "my-local-header": "local header",
     "controller-level-header": "controller header",
     "router-level-header": "router header",
     "app-level-header": "app header"
   }

The respective descriptions will be used for the OpenAPI documentation.


.. tip::

    :class:`ResponseHeader <litestar.datastructures.response_header.ResponseHeader>` is
    a special class that allows to add OpenAPI attributes such as `description` or `documentation_only`.
    If you don't need those, you can optionally define `response_headers` using a mapping - such as a dictionary -
    as well:

    .. code-block:: python

        @get(response_headers={"my-header": "header-value"})
        async def handler() -> str: ...



Setting Headers Dynamically
+++++++++++++++++++++++++++

The above detailed scheme works great for statically configured headers, but how would you go about handling dynamically
setting headers? Litestar allows you to set headers dynamically in several ways and below we will detail the two
primary patterns.

Using Annotated Responses
^^^^^^^^^^^^^^^^^^^^^^^^^

We can simply return a response instance directly from the route handler and set the headers dictionary manually
as you see fit, e.g.:

.. literalinclude:: /examples/responses/response_headers_2.py
    :language: python


In the above we use the ``response_headers`` kwarg to pass the ``name`` and ``description`` parameters for the ``Random-Header``
to the OpenAPI documentation, but we set the value dynamically in as part of
the :ref:`annotated response <usage/responses/returning_responses:Annotating responses>` we return. To this end we do not set a ``value``
for it and we designate it as ``documentation_only=True``.

Using the After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative pattern would be to use an :ref:`after request handler <after_request>`. We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the headers on the corresponding layer:

.. literalinclude:: /examples/responses/response_headers_3.py
    :language: python


In the above we set the response header using an ``after_request_handler`` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granularly by overriding header specification as
required. For example, lets say we have a router level header being set and a local header with the same key but a
different value range:

.. literalinclude:: /examples/responses/response_headers_4.py
    :language: python


Predefined Headers
++++++++++++++++++

Litestar has a dedicated implementation for a few commonly used headers. These headers can be set separately
with dedicated keyword arguments or as class attributes on all layers of the app (individual route handlers, controllers,
routers, and the app itself). Each layer overrides the layer above it - thus, the headers defined for a specific route
handler will override those defined on its router, which will in turn override those defined on the app level.

These header implementations allow easy creating, serialization and parsing according to the associated header
specifications.

Cache Control
^^^^^^^^^^^^^

:class:`CacheControlHeader <.datastructures.headers.CacheControlHeader>` represents a
`Cache-Control Header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control>`_.

Here is a simple example that shows how to use it:

.. literalinclude:: /examples/datastructures/headers/cache_control.py
    :caption: Cache Control Header
    :language: python


In this example we have a ``cache-control`` with ``max-age`` of 1 month for the whole app, a ``max-age`` of
1 day for all routes within ``MyController``, and ``no-store`` for one specific route ``get_server_time``. Here are the cache
control values that will be returned from each endpoint:


* When calling ``/population`` the response will have ``cache-control`` with ``max-age=2628288`` (1 month).
* When calling ``/chance_of_rain`` the response will have ``cache-control`` with ``max-age=86400`` (1 day).
* When calling ``/timestamp`` the response will have ``cache-control`` with ``no-store`` which means don't store the result
  in any cache.

ETag
^^^^

:class:`ETag <.datastructures.headers.ETag>` represents an
`ETag header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag>`_.

Here are some usage examples:

.. literalinclude:: /examples/datastructures/headers/etag.py
    :caption: Returning ETag headers
    :language: python


.. literalinclude:: /examples/datastructures/headers/etag_parsing.py
   :caption: Parsing ETag headers
   :language: python


Setting Response Cookies
-------------------------

Litestar allows you to define response cookies by using the ``response_cookies`` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers, and the app
itself:

.. literalinclude:: /examples/responses/response_cookies_1.py
    :language: python


In the above example, the response returned by ``my_route_handler`` will have cookies set by each layer of the
application. Cookies are set using
the `Set-Cookie header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie>`_ and with above resulting
in:

.. code-block:: text

   Set-Cookie: local-cookie=local value; Path=/; SameSite=lax
   Set-Cookie: controller-cookie=controller value; Path=/; SameSite=lax
   Set-Cookie: router-cookie=router value; Path=/; SameSite=lax
   Set-Cookie: app-cookie=app value; Path=/; SameSite=lax

You can easily override cookies declared in higher levels by redeclaring a cookie with the same key in a lower level,
e.g.:

.. literalinclude:: /examples/responses/response_cookies_2.py
    :language: python


Of the two declarations of ``my-cookie`` only the route handler one will be used, because its lower level:

.. code-block:: text

   Set-Cookie: my-cookie=456; Path=/; SameSite=lax



.. tip::

    If all you need for your cookies are key and value, you can supply them using a :class:`Mapping[str, str] <typing.Mapping>`
    - like a :class:`dict` - instead:

    .. code-block:: python

        @get(response_cookies={"my-cookie": "cookie-value"})
        async def handler() -> str: ...


.. seealso::

    * :class:`Cookie reference <.datastructures.cookie.Cookie>`



Setting Cookies dynamically
++++++++++++++++++++++++++++

While the above scheme works great for static cookie values, it doesn't allow for dynamic cookies. Because cookies are
fundamentally a type of response header, we can utilize the same patterns we use to
setting :ref:`set headers headers <usage/responses/headers_and_cookies:Setting Headers Dynamically>`.

Using Annotated Responses
^^^^^^^^^^^^^^^^^^^^^^^^^

We can simply return a response instance directly from the route handler and set the cookies list manually
as you see fit, e.g.:

.. literalinclude:: /examples/responses/response_cookies_3.py
    :language: python


In the above we use the ``response_cookies`` kwarg to pass the ``key`` and ``description`` parameters for the ``Random-Cookie``
to the OpenAPI documentation, but we set the value dynamically in as part of
the :ref:`annotated response <usage/responses/returning_responses:Annotating responses>` we return. To this end we do not set a ``value``
for it and we designate it as ``documentation_only=True``.

Using the After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative pattern would be to use an :ref:`after request handler <after_request>`. We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the cookies on the corresponding layer:

.. literalinclude:: /examples/responses/response_cookies_4.py
    :language: python


In the above we set the cookie using an ``after_request_handler`` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granular by overriding cookie specification as
required. For example, lets say we have a router level cookie being set and a local cookie with the same key but a
different value range:

.. literalinclude:: /examples/responses/response_cookies_5.py
   :language: python
