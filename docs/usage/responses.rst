Responses
=========

Litestar supports various methods for specifying and handling HTTP responses, each suitable for different scenarios.
The fundamental approach is straightforward: return a value from the route handler function,
and Litestar handles the rest.

.. code-block:: python
    :caption: Returning a Pydantic ``BaseModel`` Instance from a Route Handler

    from pydantic import BaseModel
    from litestar import get


    class Resource(BaseModel):
       id: int
       name: str


    @get("/resources")
    def retrieve_resource() -> Resource:
       return Resource(id=1, name="my resource")

In the example above, the route handler function returns an instance of the ``Resource`` pydantic class.
This value will then be used by Litestar to construct an instance of the :class:`Response <litestar.response.Response>`
class using defaults values: the response status code will be set to ``200`` and it is ``Content-Type`` header
will be set to ``application/json``.

The ``Resource`` instance will be serialized into JSON and set as the response body.

Media Type
----------

You do not have to specify the :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` kwarg in the route
handler function if the response should be JSON.
But if you wish to return a response other than JSON, you should specify this value.
You can use the :class:`MediaType <litestar.enums.MediaType>` enum for this purpose:

.. code-block:: python
    :caption: Specifying a Non-JSON Media Type in a Route Handler

    from litestar import MediaType, get


    @get("/resources", media_type=MediaType.TEXT)
    def retrieve_resource() -> str:
       return "The rumbling rabbit ran around the rock"

The value of the :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` kwarg affects both the
serialization of response data and the generation of OpenAPI docs.
The above example will cause Litestar to serialize the response as a simple bytes string with a ``Content-Type``
header value of ``text/plain``. It will also set the corresponding values in the OpenAPI documentation.

:class:`MediaType <litestar.enums.MediaType>` has the following members:

* :paramref:`MediaType.JSON <litestar.enums.MediaType.JSON>`: ``application/json``
* :paramref:`MediaType.MessagePack <litestar.enums.MediaType.MESSAGEPACK>`: ``application/x-msgpack``
* :paramref:`MediaType.TEXT <litestar.enums.MediaType.TEXT>`: ``text/plain``
* :paramref:`MediaType.HTML <litestar.enums.MediaType.HTML>`: ``text/html``
* :paramref:`MediaType.CSS <litestar.enums.MediaType.CSS>`: ``text/css``
* :paramref:`MediaType.XML <litestar.enums.MediaType.XML>`: ``application/xml``

You can also set any `IANA referenced <https://www.iana.org/assignments/media-types/media-types.xhtml>`_ media type
string as the :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type`. While this will still affect the
OpenAPI generation as expected, you might need to handle serialization using either a
:ref:`custom response <usage/responses:Custom Responses>` with serializer or by serializing the value in the
route handler function.

JSON Responses
++++++++++++++

As previously mentioned, the default :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` is
:paramref:`MediaType.JSON <litestar.enums.MediaType.JSON>` which supports the following values:

* :doc:`Dataclasses <python:library/dataclasses>`
* `Pydantic dataclasses <https://docs.pydantic.dev/usage/dataclasses/>`_
* `Pydantic models <https://docs.pydantic.dev/usage/models/>`_
* Models from libraries that extend pydantic models
* :class:`UUIDs <uuid.UUID>`
* :doc:`Datetime <python:library/datetime>` objects
* `msgspec.Struct <https://jcristharif.com/msgspec/structs.html>`_
* Container types such as :class:`dict` or :class:`list` containing supported types

If you need to return other values and would like to extend serialization you can do
this :ref:`custom responses <usage/responses:Custom Responses>`.

You can also set an application media type string with the ``+json`` suffix
defined in `RFC 6839 <https://datatracker.ietf.org/doc/html/rfc6839#section-3.1>`_
as the :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` and it will be recognized and serialized as json.

For example, you can use ``application/problem+json``
(see `RFC 7807 <https://datatracker.ietf.org/doc/html/rfc7807#section-6.1>`_)
and it will work just like json but have the appropriate content-type header
and show up in the generated OpenAPI schema.

.. literalinclude:: /examples/responses/json_suffix_responses.py
    :caption: Demonstrating Custom JSON Suffix Responses

MessagePack Responses
+++++++++++++++++++++

In addition to JSON, Litestar offers support for the `MessagePack <https://msgpack.org/>`_
format which can be a time and space efficient alternative to JSON.

It supports all the same types as JSON serialization. To send a ``MessagePack`` response,
simply specify the media type as :paramref:`MediaType.MessagePack <litestar.enums.MediaType.MESSAGEPACK>`:

.. code-block:: python
    :caption: Using :paramref:`MediaType.MessagePack <litestar.enums.MediaType.MESSAGEPACK>` for
      MessagePack responses

    from typing import Dict
    from litestar import get, MediaType


    @get(path="/health-check", media_type=MediaType.MESSAGEPACK)
    def health_check() -> Dict[str, str]:
       return {"hello": "world"}

Plaintext responses
+++++++++++++++++++

For :paramref:`MediaType.Text <litestar.enums.MediaType.Text>`, route handlers should return
a :class:`str` or :class:`bytes` value:

.. code-block:: python
    :caption: Using :paramref:`MediaType.Text <litestar.enums.MediaType.Text>` for plaintext responses

    from litestar import get, MediaType


    @get(path="/health-check", media_type=MediaType.TEXT)
    def health_check() -> str:
       return "healthy"

HTML responses
++++++++++++++

For :paramref:`MediaType.HTML <litestar.enums.MediaType.HTML>`, route handlers should return
a :class:`str` or :class:`bytes` value that contains HTML:

.. code-block:: python
    :caption: Using :paramref:`MediaType.HTML <litestar.enums.MediaType.HTML>` for HTML responses

    from litestar import get, MediaType


    @get(path="/page", media_type=MediaType.HTML)
    def health_check() -> str:
       return """
       <html>
           <body>
               <div>
                   <span>Hello World!</span>
               </div>
           </body>
       </html>
       """

It is a good idea to use a :ref:`template engine <usage/templating:template engines>` for more
complex HTML responses and to write the template itself in a separate file rather than a string.

Content Negotiation
-------------------

If your handler can return data with different media types and you want to use
`Content Negotiation <https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation>`_
to allow the client to choose which type to return, you can use the
:attr:`Request.accept <litestar.connection.Request.accept>` property to
calculate the best matching return media type.

.. dropdown:: Content negotiation based on the Accept header

    .. literalinclude:: /examples/responses/response_content.py
        :caption: Content negotiation based on the Accept header

Status Codes
------------

You can control the response :paramref:`~litestar.handlers.HTTPRouteHandler.params.status_code` by setting
the corresponding kwarg to the desired value:

.. dropdown:: Setting a custom status code

    .. code-block:: python
        :caption: Setting a custom status code

        from pydantic import BaseModel
        from litestar import get
        from litestar.status_codes import HTTP_202_ACCEPTED


        class Resource(BaseModel):
           id: int
           name: str


        @get("/resources", status_code=HTTP_202_ACCEPTED)
        def retrieve_resource() -> Resource:
           return Resource(id=1, name="my resource")

If :paramref:`~litestar.handlers.HTTPRouteHandler.params.status_code` is not set by the user,
the following defaults are used:

* :paramref:`~litestar.enums.HttpMethod.POST`: ``201 (Created)``
* :paramref:`~litestar.enums.HttpMethod.DELETE`: ``204 (No Content)``
* :paramref:`~litestar.enums.HttpMethod.GET`,
  :paramref:`~litestar.enums.HttpMethod.PATCH`,
  :paramref:`~litestar.enums.HttpMethod.PUT`: ``200 (Ok)``

.. attention:: For status codes < ``100`` or ``204``, ``304`` statuses, no response body is allowed.
    If you specify a return annotation other than ``None``, an
    :class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>` will be raised.

When using the :class:`route <litestar.handlers.http_handlers.base.HTTPRouteHandler>` decorator with
multiple http methods, the default status code is ``200``.

The default for :class:`get <.handlers.delete>` is ``204`` because by default it is assumed that delete operations
return no data. This though might not be the case in your implementation - so take care of setting it as you see fit.

While you can write integers as the value for :paramref:`~litestar.handlers.HTTPRouteHandler.params.status_code`,
e.g. ``200``, it is best practice to use constants (also in tests).

Litestar includes easy to use statuses that are exported from :doc:`litestar.status_codes`,
e.g. :data:`~litestar.status_codes.HTTP_200_OK` and :data:`~litestar.status_codes.HTTP_201_CREATED`.

Another option is the :class:`http.HTTPStatus` enum from the standard library, which also offers
extra functionality.

Returning responses
-------------------

While the default response handling fits most use cases, in some cases you need to be able to
return a response instance directly.

Litestar allows you to return any class inheriting from the :class:`Response <litestar.response.Response>` class.
Thus, the below example will work perfectly fine:

.. dropdown:: Returning a custom response with headers and cookies

    .. literalinclude:: /examples/responses/returning_responses.py
        :caption: Returning a custom response with headers and cookies

.. attention:: In the case of the builtin :class:`Template <litestar.response.Template>`,
    :class:`File <litestar.response.File>`, :class:`Stream <litestar.response.Stream>`, and
    :class:`Redirect <litestar.response.Redirect>` you should use the response "response containers", otherwise
    OpenAPI documentation will not be generated correctly. For more details see the respective documentation sections:

    - `Template responses`_
    - `File responses`_
    - `Streaming responses`_
    - `Redirect responses`_

Annotating responses
++++++++++++++++++++

As you can see above, the :class:`Response <litestar.response.Response>` class accepts a generic argument.
This allows Litestar to infer the response body when generating the OpenAPI docs.

.. note:: If the generic argument is not provided, and thus defaults to ``Any``, the OpenAPI docs
    will be imprecise. So make sure to type this argument even when returning an empty or ``null`` body,
    i.e. use ``None``.

Returning ASGI Applications
+++++++++++++++++++++++++++

Litestar also supports returning ASGI applications directly, as you would responses. For example:

.. code-block:: python
    :caption: Returning an ASGI application from a route handler

    from litestar import get
    from litestar.types import ASGIApp, Receive, Scope, Send


    @get("/")
    def handler() -> ASGIApp:
       async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None: ...

       return my_asgi_app

What is an ASGI Application?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An ASGI application in this context is any async :term:`callable <python:callable>`
(function, class method or simply a class that implements that special :meth:`object.__call__` dunder method)
that accepts the three ASGI arguments: ``scope``, ``receive``, and ``send``.

For example, all the following examples are ASGI applications:

.. dropdown:: Function ASGI Application


    .. code-block:: python
        :caption: Function-based ASGI Application

        from litestar.types import Receive, Scope, Send


        async def my_asgi_app_function(scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...

.. dropdown:: Method ASGI Application

    .. code-block:: python
        :caption: Method-based ASGI Application

        from litestar.types import Receive, Scope, Send


        class MyClass:
           async def my_asgi_app_method(
               self, scope: Scope, receive: Receive, send: Send
           ) -> None:
               # do something here
               ...

.. dropdown:: Class ASGI Application

    .. code-block:: python
        :caption: Class-based ASGI Application

        from litestar.types import Receive, Scope, Send


        class ASGIApp:
           async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
               # do something here
               ...

Returning responses from third-party libraries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because you can return any ASGI Application from a route handler, you can also use any ASGI application from other
libraries. For example, you can return the response classes from Starlette or FastAPI directly from route handlers:

.. code-block:: python
    :caption: Returning a Starlette JSONResponse from a route handler

    from starlette.responses import JSONResponse

    from litestar import get
    from litestar.types import ASGIApp


    @get("/")
    def handler() -> ASGIApp:
       return JSONResponse(content={"hello": "world"})  # type: ignore

.. attention:: Litestar offers strong typing for the ASGI arguments.
    Other libraries often offer less strict typing, which might cause type checkers to complain when using ASGI apps
    from them inside Litestar. For the time being, the only solution is to add ``# type: ignore`` comments
    in the pertinent places. Nonetheless, the above example will work perfectly fine.

Setting Response Headers
------------------------

Litestar allows you to define response headers by using the ``response_headers`` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers, and the app
itself:

.. dropdown:: Setting response headers at different levels of the application

    .. literalinclude:: /examples/responses/response_headers_1.py
        :caption: Setting response headers at different levels of the application through
          :ref:`usage/applications:layered architecture`

In the above example the response returned from ``my_route_handler`` will have headers set from each layer of the
application using the given key+value combinations. I.e. it will be a dictionary equal to this:

.. code-block:: json
    :caption: Response headers dictionary

    {
     "my-local-header": "local header",
     "controller-level-header": "controller header",
     "router-level-header": "router header",
     "app-level-header": "app header"
    }

The respective descriptions will be used for the OpenAPI documentation.

.. tip:: :class:`ResponseHeader <litestar.datastructures.response_header.ResponseHeader>` is
    a special class that allows to add OpenAPI attributes such as
    :paramref:`~litestar.datastructures.response_header.ResponseHeader.description` or
    :paramref:`~litestar.datastructures.response_header.ResponseHeader.documentation_only` to the header.

    If you do not need those, you can optionally define
    :paramref:`~litestar.datastructures.response_header.ResponseHeader.documentation_only`
    using a mapping - such as a dictionary - as well:

    .. code-block:: python
        :caption: Example of setting response headers at different levels of the application using a dictionary

        @get(response_headers={"my-header": "header-value"})
        async def handler() -> str: ...

Setting Headers Dynamically
+++++++++++++++++++++++++++

The above detailed scheme works great for statically configured headers, but how would you go about handling
dynamically setting headers?
Litestar allows you to set headers dynamically in several ways and below we will detail the two primary patterns.

Using Annotated Responses
^^^^^^^^^^^^^^^^^^^^^^^^^

We can simply return a response instance directly from the route handler and set the headers dictionary manually
as you see fit, e.g.:

.. dropdown:: Setting response headers dynamically in an annotated response

    .. literalinclude:: /examples/responses/response_headers_2.py
        :caption: Setting response headers dynamically in an annotated response

In the above we use the ``response_headers`` kwarg to pass the
:paramref:`~litestar.datastructures.response_header.ResponseHeader.name` and
:paramref:`~litestar.datastructures.response_header.ResponseHeader.description` parameters for the ``Random-Header``
to the OpenAPI documentation, but we set the value dynamically in as part of
the :ref:`annotated response <usage/responses:annotating responses>` we return.

To this end we do not set a :paramref:`~litestar.datastructures.response_header.ResponseHeader.value` for it and
we designate it as :paramref:`~litestar.datastructures.response_header.ResponseHeader.documentation_only`
by setting it to ``True``.

Using the After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative pattern would be to use an :ref:`after request handler <after_request>`. We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care
to document the headers on the corresponding layer:

.. dropdown:: Setting response headers dynamically in an ``after_request_handler``

    .. literalinclude:: /examples/responses/response_headers_3.py
        :caption: Setting response headers dynamically in an annotated response and after request handler

In the above we set the response header using an ``after_request_handler`` function on the router level,
passed into the :paramref:`~litestar.router.Router.after_request` parameter.
Because the handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granularly by overriding header specification
as required. For example, let us say we have a router level header being set and a local header with the
same key but a different value range:

.. dropdown:: Overriding response header documentation at different levels of the application

    .. literalinclude:: /examples/responses/response_headers_4.py
        :caption: Overriding response header documentation at different levels of the application

Predefined Headers
++++++++++++++++++

Litestar has a dedicated implementation for a few commonly used headers. These headers can be set separately
with dedicated keyword arguments or as class attributes on all layers of the app (individual route handlers,
controllers, routers, and the app itself). Each layer overrides the layer above it - thus, the headers
defined for a specific route handler will override those defined on its router, which will in turn override
those defined on the app level.

These header implementations allow easy creating, serialization and parsing according to the associated header
specifications.

Cache Control
^^^^^^^^^^^^^

:class:`CacheControlHeader <.datastructures.headers.CacheControlHeader>` represents a
`Cache-Control Header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control>`_.

.. dropdown:: Cache Control Header Usage Examples

    .. literalinclude:: /examples/datastructures/headers/cache_control.py
        :caption: Cache Control Header

In this example we have a :paramref:`~litestar.app.Litestar.cache-control` with a
:paramref:`~litestar.datastructures.headers.CacheControlHeader.max-age` of 1 month for the whole app, a
:paramref:`~litestar.datastructures.headers.CacheControlHeader.max-age` of 1 day for all routes within
``MyController``, and :paramref:`~litestar.datastructures.headers.CacheControlHeader.no-store` for one
specific route ``get_server_time``.

Here are the cache control values that will be returned from each endpoint:

* When calling ``/population`` the response will have :paramref:`~litestar.app.Litestar.cache-control` with
  :paramref:`~litestar.datastructures.headers.CacheControlHeader.max-age` set to ``2628288`` (1 month).
* When calling ``/chance_of_rain`` the response will have :paramref:`~litestar.app.Litestar.cache-control` with
  :paramref:`~litestar.datastructures.headers.CacheControlHeader.max-age` set to ``86400`` (1 day).
* When calling ``/timestamp`` the response will have :paramref:`~litestar.app.Litestar.cache-control` with
  :paramref:`~litestar.datastructures.headers.CacheControlHeader.no-store` which means do not store the result
  in any cache.

ETag
^^^^

:class:`ETag <.datastructures.headers.ETag>` represents an
`ETag header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag>`_.

.. dropdown:: ETag header Usage Examples

    .. literalinclude:: /examples/datastructures/headers/etag.py
        :caption: Returning ETag headers

    .. literalinclude:: /examples/datastructures/headers/etag_parsing.py
       :caption: Parsing ETag headers

Setting Response Cookies
------------------------

Litestar allows you to define response cookies by using the ``response_cookies`` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers, and the app
itself:

.. dropdown:: Setting response cookies at different levels of the application

    .. literalinclude:: /examples/responses/response_cookies_1.py
        :caption: Setting response cookies at different levels of the application through

In the above example, the response returned by ``my_route_handler`` will have cookies set by
each layer of the application. Cookies are set using the
`Set-Cookie header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie>`_ and with
above resulting in:

.. code-block:: text
    :caption: Resulting Set-Cookie headers

    Set-Cookie: local-cookie=local value; Path=/; SameSite=lax
    Set-Cookie: controller-cookie=controller value; Path=/; SameSite=lax
    Set-Cookie: router-cookie=router value; Path=/; SameSite=lax
    Set-Cookie: app-cookie=app value; Path=/; SameSite=lax

You can easily override cookies declared in higher levels by re-declaring a cookie with the
same key in a lower level e.g.,:

.. literalinclude:: /examples/responses/response_cookies_2.py
    :caption: Overriding response cookies at different levels of the application

Of the two declarations of ``my-cookie`` only the route handler one will be used, because it is lower level:

.. code-block:: text
    :caption: Resulting Set-Cookie header

    Set-Cookie: my-cookie=456; Path=/; SameSite=lax

.. tip:: If all you need for your cookies are key and value, you can supply them using a
    :class:`Mapping[str, str] <typing.Mapping>` - like a :class:`dict` - instead:

    .. code-block:: python
        :caption: Using a dictionary for response cookies

        @get(response_cookies={"my-cookie": "cookie-value"})
        async def handler() -> str: ...

.. seealso:: * :class:`Cookie reference <.datastructures.cookie.Cookie>`

Setting Cookies dynamically
++++++++++++++++++++++++++++

While the above scheme works great for static cookie values, it does not allow for dynamic cookies. Because cookies are
fundamentally a type of response header, we can utilize the same patterns we use to
setting :ref:`set headers headers <usage/responses:setting headers dynamically>`.

Using Annotated Responses
^^^^^^^^^^^^^^^^^^^^^^^^^

We can simply return a response instance directly from the route handler and set the cookies list manually
as you see fit, e.g.:

.. dropdown:: Setting response cookies dynamically in an annotated response

    .. literalinclude:: /examples/responses/response_cookies_3.py
        :caption: Setting response cookies dynamically in an annotated response

In the above we use the :paramref:`~litestar.handlers.http_handlers.decorators.get.response_cookies` kwarg
to pass the :paramref:`~litestar.datastructures.response_header.ResponseHeader.key` and
:paramref:`~litestar.datastructures.response_header.ResponseHeader.description` parameters for
the ``Random-Cookie`` to the OpenAPI documentation, but we set the value dynamically in as part of
the :ref:`annotated response <usage/responses:annotating responses>` we return. To this end we do not
set a :paramref:`~litestar.datastructures.response_header.ResponseHeader.value` for it and we designate
it as :paramref:`~litestar.datastructures.response_header.ResponseHeader.documentation_only` by setting it to ``True``.

Using the After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative pattern would be to use an :ref:`after request handler <after_request>`. We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the cookies on the corresponding layer:

.. dropdown:: Setting response cookies dynamically in an ``after_request_handler``

    .. literalinclude:: /examples/responses/response_cookies_4.py
        :caption: Setting response cookies dynamically in an ``after_request_handler``

In the above we set the cookie using an ``after_request_handler`` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granular by overriding cookie specification as
required. For example, let us say we have a router level cookie being set and a local cookie with the same key but a
different value range:

.. dropdown:: Overriding response cookie documentation at different levels of the application

    .. literalinclude:: /examples/responses/response_cookies_5.py
        :caption: Overriding response cookie documentation at different levels of the application

Redirect Responses
------------------

Redirect responses are `special HTTP responses <https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections>`_
with a status code in the ``30x`` range.

In Litestar, a redirect response looks like this:

.. code-block:: python
    :caption: Returning a redirect response

    from litestar.status_codes import HTTP_302_FOUND
    from litestar import get
    from litestar.response import Redirect


    @get(path="/some-path", status_code=HTTP_302_FOUND)
    def redirect() -> Redirect:
       # do some stuff here
       # ...
       # finally return redirect
       return Redirect(path="/other-path")

To return a redirect response you should do the following:

* Optionally: set an appropriate :data:`~litestar.response.redirect.RedirectStatusType` status code for the
  route handler (``301``, ``302``, ``303``, ``307``, ``308``). If not set, the default of ``302`` will be used.
* Annotate the return value of the route handler as returning :class:`Redirect <.response.Redirect>`
* Return an instance of the :class:`Redirect <.response.Redirect>` class with the desired redirect path

File Responses
--------------

File responses send a file:

.. code-block:: python
    :caption: Returning a file response

    from pathlib import Path
    from litestar import get
    from litestar.response import File


    @get(path="/file-download")
    def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )

The :class:`File <.response.File>` class expects two kwargs:

* :paramref:`~litestar.response.File.path`: the path of the file to download.
* :paramref:`~litestar.response.File.filename`: the filename to set in the
  response `Content-Disposition <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition>`_
  attachment.

When a route handler's return value is annotated with :class:`File <.response.File>`, the default
:paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` for the route_handler is switched from
:class:`MediaType.JSON <.enums.MediaType>` to :class:`MediaType.TEXT <.enums.MediaType>` (i.e. ``"text/plain"``).
If the file being sent has an `IANA media type <https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types>`_,
you should set it as the value for :paramref:`~litestar.handlers.HTTPRouteHandler.params.media_type` instead.

For example:

.. code-block:: python
    :caption: Setting the media type for a file response

    from pathlib import Path
    from litestar import get
    from litestar.response import File


    @get(path="/file-download", media_type="application/pdf")
    def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )


Streaming Responses
-------------------

To return a streaming response use the :class:`Stream <.response.Stream>` class. The class
receives a single positional arg, that must be an :term:`iterator <python:iterator>`. delivering the stream:

.. dropdown:: Returning a streaming response

    .. literalinclude:: /examples/responses/streaming_responses.py
        :caption: Returning a streaming response

You can use different kinds of values for the iterator. It can be a callable returning a
sync or async generator, a generator itself, a sync or async iterator class, or
an instance of a sync or async iterator class.

Server Sent Event Responses
---------------------------

To send ``server-sent-events`` or SSEs to the frontend, use the
:class:`ServerSentEvent <.response.ServerSentEvent>` class which receives a
:paramref:`~litestar.response.ServerSentEvent.params.content` parameter.

You can additionally specify:

* :paramref:`~litestar.response.ServerSentEvent.params.event_type`, which is the name of the event as declared
  in the browser
* :paramref:`~litestar.response.ServerSentEvent.params.event_id`, which sets the event source property
* :paramref:`~litestar.response.ServerSentEvent.params.comment_message`, which is used in for sending pings
* :paramref:`~litestar.response.ServerSentEvent.params.retry_duration`, which dictates the duration for retrying.

.. dropdown:: Returning a server-sent event response

    .. literalinclude:: /examples/responses/sse_responses.py
        :caption: Returning a server-sent event response

.. note:: You can use different kinds of values for the iterator.
    It can be a :term:`callable <python:callable>` returning a sync or async generator,
    a :term:`generator <python:generator>` itself, a :term:`sync iterator <python:iterator>`
    or :term:`async iterator <python:asynchronous iterator>` class,
    or an instance of a sync or async iterator class.

In your iterator function you can yield :class:`integers <int>`, :class:`strings <str>` or :class:`bytes`,
the message sent in that case will have ``message`` as the
:paramref:`~litestar.response.ServerSentEvent.params.event_type` if the
:class:`ServerSentEvent <.response.ServerSentEvent>` has no
:paramref:`~litestar.response.ServerSentEvent.params.event_type` set, otherwise it will use the
:paramref:`~litestar.response.ServerSentEvent.params.event_type` specified, and the data will be the yielded value.

If you want to send a different event type, you can use a dictionary with the keys
:paramref:`~litestar.response.ServerSentEvent.params.event_type` and ``data`` or
the :class:`ServerSentMessage <.response.ServerSentEventMessage>` class.

.. note:: You can further customize all the sse parameters, add comments, and set the retry duration
    by using the :class:`ServerSentEvent <.response.ServerSentEvent>` class directly
    or by using the :class:`ServerSentEventMessage <.response.ServerSentEventMessage>`
    or dictionaries with the appropriate keys.

Template Responses
------------------

Template responses are used to render templates into HTML. To use a template response you must first
:ref:`register a template engine <usage/templating:registering a template engine>` on the application level. Once an
engine is in place, you can use a template response like so:

.. code-block:: python
    :caption: test

    from litestar import Request, get
    from litestar.response import Template


    @get(path="/info")
    def info(request: Request) -> Template:
       return Template(template_name="info.html", context={"user": request.user})

In the above example, :class:`Template <.response.Template>` is passed the template name, which is a
path like value, and a context dictionary that maps string keys into values that will be rendered in the template.

Custom Responses
----------------

While Litestar supports the serialization of many types by default, sometimes you want to return something
that is not supported. In those cases it is convenient to make use of a custom response class.

The example below illustrates how to deal with :class:`MultiDict <.datastructures.MultiDict>`
instances.

.. literalinclude:: /examples/responses/custom_responses.py
    :caption: Creating a custom response class for :class:`MultiDict <.datastructures.MultiDict>` instances

.. admonition:: Layered architecture
    :class: seealso

    Response classes are part of Litestar's layered architecture, which means you can
    set a response class on every layer of the application. If you have set a response
    class on multiple layers, the layer closest to the route handler will take precedence.

    You can read more about this here: :ref:`usage/applications:layered architecture`

Background Tasks
----------------

All Litestar responses allow passing in a :paramref:`~litestar.response.base.ASGIResponse.background` kwarg.
This kwarg accepts:

* :class:`BackgroundTask <.background_tasks.BackgroundTask>`
* An instance of :class:`BackgroundTasks <.background_tasks.BackgroundTasks>`, which wraps an iterable of
  :class:`BackgroundTask <.background_tasks.BackgroundTask>` instances.
* ``None`` (the default)

A background task is a sync or async :term:`callable <python:callable>`
(function, method, or class that implements the :meth:`object.__call__` dunder method) that
will be called after the response finishes sending the data.

Thus, in the following example the passed in background task will be executed after the response sends:

.. dropdown:: Background Task Passed into Response

    .. literalinclude:: /examples/responses/background_tasks_1.py
        :caption: Background Task Passed into Response

When the ``greeter`` handler is called, the logging task will be called with any ``*args`` and ``**kwargs`` passed
into the :class:`BackgroundTask <.background_tasks.BackgroundTask>`.

.. note:: In the above example ``"greeter"`` is an arg and ``message=f"was called with name {name}"`` is a kwarg.
    The function signature of ``logging_task`` allows for this, so this should pose no problem.
    :class:`BackgroundTask <.background_tasks.BackgroundTask>` is typed with :class:`ParamSpec <typing.ParamSpec>`,
    enabling correct type checking for arguments and keyword arguments passed to it.

Route decorators (e.g. :class:`@get() <.handlers.get>`, :class:`@post() <.handlers.post>`, etc.) also allow
passing in a background task with the ``background`` kwarg:

.. dropdown:: Background Task Passed into Decorator

    .. literalinclude:: /examples/responses/background_tasks_2.py
        :caption: Background Task Passed into Decorator

Route handler arguments cannot be passed into background tasks when they are passed into decorators.

Executing Multiple Background Tasks
+++++++++++++++++++++++++++++++++++

You can also use the :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` class and pass to it an
:term:`callable <python:iterable>` (:class:`list`, :class:`tuple`, etc.) of
:class:`BackgroundTask <.background_tasks.BackgroundTask>` instances:

.. dropdown:: Multiple Background Tasks

    .. literalinclude:: /examples/responses/background_tasks_3.py
        :caption: Multiple Background Tasks

:class:`BackgroundTasks <.background_tasks.BackgroundTasks>` class
accepts an optional keyword argument :paramref:`~litestar.background_tasks.BackgroundTasks.run_in_task_group` with
a default value of ``False``. Setting this to ``True`` allows background tasks to run concurrently, using an
:class:`TaskGroup <anyio.abc.TaskGroup>`.

Setting :paramref:`~litestar.background_tasks.BackgroundTasks.run_in_task_group` to ``True`` will
not preserve execution order.

Pagination
----------

When you need to return a large number of items from an endpoint it is common practice to use pagination to ensure
clients can request a specific subset or "page" from the total dataset. Litestar supports three types of
pagination out of the box:

* Classic pagination
* Limit / Offset pagination
* Cursor pagination

Classic Pagination
++++++++++++++++++

In classic pagination the dataset is divided into pages of a specific size and the consumer then
requests a specific page.

.. dropdown:: Classic Pagination Example

    .. literalinclude:: /examples/pagination/using_classic_pagination.py
        :caption: Classic Pagination

The data container for this pagination is called :class:`ClassicPagination <.pagination.ClassicPagination>`,
which is what will be returned by the paginator in the above example
This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncClassicPaginator <.pagination.AbstractAsyncClassicPaginator>` instead of the
:class:`AbstractSyncClassicPaginator <.pagination.AbstractSyncClassicPaginator>`.

Offset Pagination
+++++++++++++++++

In offset pagination the consumer requests a number of items specified by ``limit`` and the ``offset`` from
the beginning of the dataset. For example, given a list of 50 items, you could request
``limit=10``, ``offset=39`` to request items 40-50.

.. dropdown:: Offset Pagination Example

    .. literalinclude:: /examples/pagination/using_offset_pagination.py
        :caption: Offset Pagination

The data container for this pagination is
called :class:`OffsetPagination <.pagination.OffsetPagination>`, which is what will be returned by the
paginator in the above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncOffsetPaginator <.pagination.AbstractAsyncOffsetPaginator>` instead of the
:class:`AbstractSyncOffsetPaginator <.pagination.AbstractSyncOffsetPaginator>`.

Offset Pagination With `SQLAlchemy <https://www.sqlalchemy.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When retrieving paginated data from the database using `SQLAlchemy <https://www.sqlalchemy.org/>`_,
the Paginator instance requires an SQLAlchemy session instance to make queries. This can be achieved with
:doc:`/usage/dependency-injection`

.. dropdown:: Offset Pagination With SQLAlchemy

    .. literalinclude:: /examples/pagination/using_offset_pagination_with_sqlalchemy.py
        :caption: Offset Pagination With SQLAlchemy

See :ref:`SQLAlchemy plugin <usage/databases/sqlalchemy/plugins/index:Plugins>` for SQLAlchemy integration.

Cursor Pagination
+++++++++++++++++

In cursor pagination the consumer requests a number of items specified by ``results_per_page`` and a ``cursor``
after which results are given. Cursor is unique identifier within the dataset that serves as a way to
point the starting position.

.. dropdown:: Cursor Pagination Example

    .. literalinclude:: /examples/pagination/using_cursor_pagination.py
        :caption: Cursor Pagination

The data container for this pagination is called :class:`CursorPagination <.pagination.CursorPagination>`, which
is what will be returned by the paginator in the above example This will also generate the corresponding
OpenAPI documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncCursorPaginator <.pagination.AbstractAsyncCursorPaginator>` instead of the
:class:`AbstractSyncCursorPaginator <.pagination.AbstractSyncCursorPaginator>`.
