Returning Responses
===================

JSON responses
--------------

As previously mentioned, the default ``media_type`` is ``MediaType.JSON``. which supports the following values:

* :doc:`dataclasses <python:library/dataclasses>`
* `pydantic dataclasses <https://docs.pydantic.dev/usage/dataclasses/>`_
* `pydantic models <https://docs.pydantic.dev/usage/models/>`_
* models from libraries that extend pydantic models
* :class:`UUIDs <uuid.UUID>`
* :doc:`datetime objects <python:library/datetime>`
* `msgspec.Struct <https://msgspec.dev/structs>`_
* container types such as :class:`dict` or :class:`list` containing supported types

If you need to return other values and would like to extend serialization you can do
this :ref:`custom responses <usage/responses/special_responses:Custom Responses>`.

You can also set an application media type string with the ``+json`` suffix
defined in `RFC 6839 <https://datatracker.ietf.org/doc/html/rfc6839#section-3.1>`_
as the ``media_type`` and it will be recognized and serialized as json.

For example, you can use ``application/vnd.example.resource+json``
and it will work just like json but have the appropriate content-type header
and show up in the generated OpenAPI schema.

.. literalinclude:: /examples/responses/json_suffix_responses.py
    :language: python

MessagePack responses
---------------------

In addition to JSON, Litestar offers support for the `MessagePack <https://msgpack.org/>`_
format which can be a time and space efficient alternative to JSON.

It supports all the same types as JSON serialization. To send a ``MessagePack`` response,
simply specify the media type as ``MediaType.MESSAGEPACK``\ :

.. code-block:: python

   from typing import Dict
   from litestar import get, MediaType


   @get(path="/health-check", media_type=MediaType.MESSAGEPACK)
   def health_check() -> Dict[str, str]:
       return {"hello": "world"}

Plaintext responses
-------------------

For ``MediaType.TEXT``, route handlers should return a :class:`str` or :class:`bytes` value:

.. code-block:: python

   from litestar import get, MediaType


   @get(path="/health-check", media_type=MediaType.TEXT)
   def health_check() -> str:
       return "healthy"

HTML responses
--------------

For ``MediaType.HTML``, route handlers should return a :class:`str` or :class:`bytes` value that contains HTML:

.. code-block:: python

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

.. tip::

   It's a good idea to use a :ref:`template engine <usage/templating:template engines>` for more complex HTML responses
   and to write the template itself in a separate file rather than a string.


Content Negotiation
-------------------

If your handler can return data with different media types and you want to use
`Content Negotiation <https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation>`_
to allow the client to choose which type to return, you can use the
:attr:`Request.accept <litestar.connection.Request.accept>` property to
calculate the best matching return media type.

.. literalinclude:: /examples/responses/response_content.py
    :language: python


Returning response instances
----------------------------

While the default response handling fits most use cases, in some cases you need to be able to return a response instance
directly.

Litestar allows you to return any class inheriting from the :class:`Response <litestar.response.Response>` class. Thus, the below
example will work perfectly fine:

.. literalinclude:: /examples/responses/returning_responses.py
    :language: python


.. attention::

    In the case of the builtin :class:`Template <litestar.response.Template>`,
    :class:`File <litestar.response.File>`, :class:`Stream <litestar.response.Stream>`, and
    :class:`Redirect <litestar.response.Redirect>` you should use the response "response containers", otherwise
    OpenAPI documentation will not be generated correctly. For more details see the respective documentation sections:

    - :ref:`Template responses <usage/responses/special_responses:Template Responses>`
    - :ref:`File responses <usage/responses/special_responses:File Responses>`
    - :ref:`Streaming responses <usage/responses/special_responses:Streaming Responses>`
    - :ref:`Redirect responses <usage/responses/returning_responses:Redirect Responses>`


Annotating responses
++++++++++++++++++++

As you can see above, the :class:`Response <litestar.response.Response>` class accepts a generic argument. This allows Litestar
to infer the response body when generating the OpenAPI docs.

.. note::

    If the generic argument is not provided, and thus defaults to ``Any``, the OpenAPI docs will be imprecise. So make sure
    to type this argument even when returning an empty or ``null`` body, i.e. use ``None``.

Returning ASGI Applications
+++++++++++++++++++++++++++

Litestar also supports returning ASGI applications directly, as you would responses. For example:

.. code-block:: python

   from litestar import get
   from litestar.types import ASGIApp, Receive, Scope, Send


   @get("/")
   def handler() -> ASGIApp:
       async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None: ...

       return my_asgi_app

What is an ASGI Application?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An ASGI application in this context is any async callable (function, class method or simply a class that implements
that special :meth:`object.__call__` dunder method) that accepts the three ASGI arguments: ``scope``, ``receive``, and
``send``.

For example, all the following examples are ASGI applications:

Function ASGI Application
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   async def my_asgi_app_function(scope: Scope, receive: Receive, send: Send) -> None:
       # do something here
       ...

Method ASGI Application
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   class MyClass:
       async def my_asgi_app_method(
           self, scope: Scope, receive: Receive, send: Send
       ) -> None:
           # do something here
           ...

Class ASGI Application
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   class ASGIApp:
       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...

Returning responses from third party libraries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because you can return any ASGI Application from a route handler, you can also use any ASGI application from other
libraries. For example, you can return the response classes from Starlette or FastAPI directly from route handlers:

.. code-block:: python

   from starlette.responses import JSONResponse

   from litestar import get
   from litestar.types import ASGIApp


   @get("/")
   def handler() -> ASGIApp:
       return JSONResponse(content={"hello": "world"})  # type: ignore

.. attention::

   Litestar offers strong typing for the ASGI arguments. Other libraries often offer less strict typing, which might
   cause type checkers to complain when using ASGI apps from them inside Litestar.
   For the time being, the only solution is to add ``# type: ignore`` comments in the pertinent places.
   Nonetheless, the above example will work perfectly fine.


Redirect Responses
------------------

Redirect responses are `special HTTP responses <https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections>`_ with a
status code in the 30x range.

In Litestar, a redirect response looks like this:

.. code-block:: python

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

- optionally: set an appropriate status code for the route handler (301, 302, 303, 307, 308). If not set the default of 302 will be used.
- annotate the return value of the route handler as returning :class:`Redirect <.response.Redirect>`
- return an instance of the :class:`Redirect <.response.Redirect>` class with the desired redirect path
