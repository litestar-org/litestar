Route handlers
==============

Route handlers are the core of Litestar. They are constructed by decorating a function or class method with one of the
handler decorators exported from Litestar.

For example:

.. code-block:: python

   from litestar import get


   @get("/")
   def greet() -> str:
       return "hello world"

In the above example, the decorator includes all the information required to define the endpoint operation for the
combination of the path ``"/"`` and the http verb ``GET``. In this case it will be a http response with a "Content-Type"
header of ``text/plain``.

What the decorator does, is wrap the function or method within a class instance that inherits from
:class:`BaseRouteHandler <.handlers.base.BaseRouteHandler>`. These classes are optimized
descriptor classes that record all the data necessary for the given function or method - this includes a modelling of
the function signature, which allows for injection of kwargs and dependencies, as well as data pertinent to OpenAPI
spec generation.


.. include:: /admonitions/sync-to-thread-info.rst


Declaring paths
---------------

All route handler decorator accept an optional path argument. This argument can be declared as a kwarg using the ``path``
key word:

.. code-block:: python

   from litestar import get


   @get(path="/some-path")
   async def my_route_handler() -> None:
       ...

It can also be passed as an argument without the key-word:

.. code-block:: python

   from litestar import get


   @get("/some-path")
   async def my_route_handler() -> None:
       ...

And the value for this argument can be either a string path, as in the above examples, or a list of string paths:

.. code-block:: python

   from litestar import get


   @get(["/some-path", "/some-other-path"])
   async def my_route_handler() -> None:
       ...

This is particularly useful when you want to have optional :ref:`path parameters <usage/routing/parameters:Path Parameters>`:

.. code-block:: python

   from litestar import get


   @get(
       ["/some-path", "/some-path/{some_id:int}"],
   )
   async def my_route_handler(some_id: int = 1) -> None:
       ...

.. _handler-function-kwargs:

"reserved" keyword arguments
----------------------------

Route handler functions or methods access various data by declaring these as annotated function kwargs. The annotated
kwargs are inspected by Litestar and then injected into the request handler.

The following sources can be accessed using annotated function kwargs:

- :ref:`path, query, header, and cookie parameters <usage/routing/parameters:the parameter function>`
- :doc:`/usage/requests`
- :doc:`injected dependencies </usage/dependency-injection>`

Additionally, you can specify the following special kwargs, what's called "reserved keywords" internally:


* ``cookies``: injects the request :class:`cookies <.datastructures.cookie.Cookie>` as a parsed dictionary.
* ``headers``: injects the request headers as an instance of :class:`Headers <.datastructures.headers.Headers>` ,
  which is a case-insensitive mapping.
* ``query`` : injects the request ``query_params`` as a parsed dictionary.
* ``request``: injects the :class:`Request <.connection.Request>` instance. Available only for `http route handlers`_
* ``scope`` : injects the ASGI scope dictionary.
* ``socket``: injects the :class:`WebSocket <.connection.WebSocket>` instance. Available only for `websocket route handlers`_
* ``state`` : injects a copy of the application :class:`State <.datastructures.state.State>`.
* ``body`` : the raw request body. Available only for `http route handlers`_

For example:

.. code-block:: python

   from typing import Any, Dict
   from litestar import Request, get
   from litestar.datastructures import Headers, State


   @get(path="/")
   async def my_request_handler(
       state: State,
       request: Request,
       headers: Headers,
       query: Dict[str, Any],
       cookies: Dict[str, Any],
   ) -> None:
       ...

.. tip::

    You can define a custom typing for your application state and then use it as a type instead of just using the
    State class from Litestar

Type annotations
----------------

Litestar enforces strict type annotations. Functions decorated by a route handler **must** have all their kwargs and
return value type annotated. If a type annotation is missing, an
:class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>` will be raised during the
application boot-up process.

There are several reasons for why this limitation is enforced:


#. to ensure best practices
#. to ensure consistent OpenAPI schema generation
#. to allow Litestar to compute during the application bootstrap all the kwargs required by a function


HTTP route handlers
-------------------

The most commonly used route handlers are those that handle http requests and responses. These route handlers all
inherit from the class :class:`HTTPRouteHandler <litestar.handlers.HTTPRouteHandler>`, which
is aliased as the decorator called :func:`route <litestar.handlers.route>`:

.. code-block:: python

   from litestar import HttpMethod, route


   @route(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
   async def my_endpoint() -> None:
       ...

As mentioned above, ``route`` does is merely an alias for ``HTTPRouteHandler``\ , thus the below code is equivalent to the one
above:

.. code-block:: python

   from litestar import HttpMethod
   from litestar.handlers.http_handlers import HTTPRouteHandler


   @HTTPRouteHandler(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
   async def my_endpoint() -> None:
       ...



Semantic handler decorators
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar also includes "semantic" decorators, that is, decorators the pre-set the ``http_method`` kwarg to a specific HTTP
verb, which correlates with their name:


* :func:`delete <litestar.handlers.delete>`
* :func:`get <litestar.handlers.get>`
* :func:`head <litestar.handlers.head>`
* :func:`patch <litestar.handlers.patch>`
* :func:`post <litestar.handlers.post>`
* :func:`put <litestar.handlers.put>`

These are used exactly like ``route`` with the sole exception that you cannot configure the ``http_method`` kwarg:

.. code-block:: python

   from litestar import delete, get, patch, post, put, head
   from litestar.dto import DTOConfig, DTOData
   from litestar.contrib.pydantic import PydanticDTO

   from pydantic import BaseModel


   class Resource(BaseModel):
       ...


   class PartialResourceDTO(PydanticDTO[Resource]):
       config = DTOConfig(partial=True)


   @get(path="/resources")
   async def list_resources() -> list[Resource]:
       ...


   @post(path="/resources")
   async def create_resource(data: Resource) -> Resource:
       ...


   @get(path="/resources/{pk:int}")
   async def retrieve_resource(pk: int) -> Resource:
       ...


   @head(path="/resources/{pk:int}")
   async def retrieve_resource_head(pk: int) -> None:
       ...


   @put(path="/resources/{pk:int}")
   async def update_resource(data: Resource, pk: int) -> Resource:
       ...


   @patch(path="/resources/{pk:int}", dto=PartialResourceDTO)
   async def partially_update_resource(
       data: DTOData[PartialResourceDTO], pk: int
   ) -> Resource:
       ...


   @delete(path="/resources/{pk:int}")
   async def delete_resource(pk: int) -> None:
       ...

Although these decorators are merely subclasses of :class:`HTTPRouteHandler <litestar.handlers.HTTPRouteHandler>`
that pre-set the ``http_method``, using *get*, *patch*, *put*, *delete*, or *post* instead of *route* makes the
code clearer and simpler.

Furthermore, in the OpenAPI specification each unique combination of http verb (e.g. "GET", "POST", etc.) and path is
regarded as a distinct `operation <https://spec.openapis.org/oas/latest.html#operation-object>`_\ , and each operation
should be distinguished by a unique ``operation_id`` and optimally also have a ``summary`` and ``description`` sections.

As such, using the ``route`` decorator is discouraged. Instead, the preferred pattern is to share code using secondary
class methods or by abstracting code to reusable functions.


Websocket route handlers
------------------------

A WebSocket connection can be handled with a :func:`websocket <litestar.handlers.WebsocketRouteHandler>` route handler.

.. note::
    The websocket handler is a low level approach, requiring to handle the socket directly,
    and dealing with keeping it open, exceptions, client disconnects, and content negotiation.

    For a more high level approach to handling WebSockets, see :doc:`/usage/websockets`

.. code-block:: python

   from litestar import WebSocket, websocket


   @websocket(path="/socket")
   async def my_websocket_handler(socket: WebSocket) -> None:
       await socket.accept()
       await socket.send_json({...})
       await socket.close()

The ``websocket`` decorator is an alias of the class
:class:`WebsocketRouteHandler <.handlers.WebsocketRouteHandler>`. Thus, the below
code is equivalent to the one above:

.. code-block:: python

   from litestar import WebSocket
   from litestar.handlers.websocket_handlers import WebsocketRouteHandler


   @WebsocketRouteHandler(path="/socket")
   async def my_websocket_handler(socket: WebSocket) -> None:
       await socket.accept()
       await socket.send_json({...})
       await socket.close()

In difference to HTTP routes handlers, websocket handlers have the following requirements:


#. they **must** declare a ``socket`` kwarg.
#. they **must** have a return annotation of ``None``.
#. they **must** be async functions.

These requirements are enforced using inspection, and if any of them is unfulfilled an informative exception will be raised.

.. note::

    OpenAPI currently does not support websockets. As such no schema will be generated for these route handlers.


.. seealso::

    * :class:`WebsocketRouteHandler <litestar.handlers.WebsocketRouteHandler>`
    * :doc:`/usage/websockets`


ASGI route handlers
-------------------

If you need to write your own ASGI application, you can do so using the :func:`asgi <litestar.handlers.asgi>` decorator:

.. code-block:: python

   from litestar.types import Scope, Receive, Send
   from litestar.status_codes import HTTP_400_BAD_REQUEST
   from litestar import Response, asgi


   @asgi(path="/my-asgi-app")
   async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
       if scope["type"] == "http":
           if scope["method"] == "GET":
               response = Response({"hello": "world"})
               await response(scope=scope, receive=receive, send=send)
           return
       response = Response(
           {"detail": "unsupported request"}, status_code=HTTP_400_BAD_REQUEST
       )
       await response(scope=scope, receive=receive, send=send)

Like other route handlers, the ``asgi`` decorator is an alias of the class
:class:`ASGIRouteHandler <.handlers.ASGIRouteHandler>`. Thus,
the code below is equivalent to the one above:

.. code-block:: python

   from litestar import Response
   from litestar.handlers.asgi_handlers import ASGIRouteHandler
   from litestar.status_codes import HTTP_400_BAD_REQUEST
   from litestar.types import Scope, Receive, Send


   @ASGIRouteHandler(path="/my-asgi-app")
   async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
       if scope["type"] == "http":
           if scope["method"] == "GET":
               response = Response({"hello": "world"})
               await response(scope=scope, receive=receive, send=send)
           return
       response = Response(
           {"detail": "unsupported request"}, status_code=HTTP_400_BAD_REQUEST
       )
       await response(scope=scope, receive=receive, send=send)

Limitations of ASGI route handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In difference to the other route handlers, the ``asgi`` route handler accepts only 3 kwargs that **must** be defined:

* ``scope`` , a mapping of values describing the ASGI connection. It always includes a ``type`` key, with the values being
  either ``http`` or ``websocket`` , and a ``path`` key. If the type is ``http`` , the scope dictionary will also include
  a ``method`` key with the value being one of ``DELETE, GET, POST, PATCH, PUT, HEAD``.
* ``receive`` , an injected function by which the ASGI application receives messages.
* ``send`` , an injected function by which the ASGI application sends messages.

You can read more about these in the `ASGI specification <https://asgi.readthedocs.io/en/latest/specs/main.html>`_.

Additionally, ASGI route handler functions **must** be async functions. This is enforced using inspection, and if the
function is not an async function, an informative exception will be raised.

See the :class:`API Reference <.handlers.asgi_handlers.ASGIRouteHandler>` for full details on the ``asgi`` decorator and the
kwargs it accepts.

Route handler indexing
----------------------

You can provide in all route handler decorators a ``name`` kwarg. The value for this kwarg **must be unique**\ , otherwise
:class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>` exception will be raised. Default
value for ``name`` is value returned by ``handler.__str__`` which should be the full dotted path to the handler
(e.g. ``app.controllers.projects.list`` for ``list`` function residing in ``app/controllers/projects.py`` file). ``name`` can
be used to dynamically retrieve (i.e. during runtime) a mapping containing the route handler instance and paths, also
it can be used to build a URL path for that handler:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.exceptions import NotFoundException
   from litestar.response import Redirect


   @get("/abc", name="one")
   def handler_one() -> None:
       pass


   @get("/xyz", name="two")
   def handler_two() -> None:
       pass


   @get("/def/{param:int}", name="three")
   def handler_three(param: int) -> None:
       pass


   @get("/{handler_name:str}", name="four")
   def handler_four(request: Request, name: str) -> Redirect:
       handler_index = request.app.get_handler_index_by_name(name)
       if not handler_index:
           raise NotFoundException(f"no handler matching the name {name} was found")

       # handler_index == { "paths": ["/"], "handler": ..., "qualname": ... }
       # do something with the handler index below, e.g. send a redirect response to the handler, or access
       # handler.opt and some values stored there etc.

       return Redirect(path=handler_index[0])


   @get("/redirect/{param_value:int}", name="five")
   def handler_five(request: Request, param_value: int) -> Redirect:
       path = request.app.route_reverse("three", param=param_value)
       return Redirect(path=path)


   app = Litestar(route_handlers=[handler_one, handler_two, handler_three])

:meth:`route_reverse <.app.Litestar.route_reverse>` will raise
:class:`NoMatchRouteFoundException <.exceptions.NoRouteMatchFoundException>` if route with given name was not found
or if any of path parameters is missing or if any of passed path parameters types do not match types in the respective
route declaration. However, :class:`str` is accepted in place of :class:`datetime.datetime`, :class:`datetime.date`,
:class:`datetime.time`, :class:`datetime.timedelta`, :class:`float`, and :class:`pathlib.Path`
parameters, so you can apply custom formatting and pass the result to ``route_reverse``.

If handler has multiple paths attached to it ``route_reverse`` will return the path that consumes the most number of
keywords arguments passed to the function.

.. code-block:: python

   from litestar import get, Request


   @get(
       ["/some-path", "/some-path/{id:int}", "/some-path/{id:int}/{val:str}"],
       name="handler_name",
   )
   def handler(id: int = 1, val: str = "default") -> None:
       ...


   @get("/path-info")
   def path_info(request: Request) -> str:
       path_optional = request.app.route_reverse("handler_name")
       # /some-path`

       path_partial = request.app.route_reverse("handler_name", id=100)
       # /some-path/100

       path_full = request.app.route_reverse("handler_name", id=100, val="value")
       # /some-path/100/value`

       return f"{path_optional} {path_partial} {path_full}"

If there are multiple paths attached to a handler that have the same path parameters (for example indexed handler
has been registered on multiple routers) the result of ``route_reverse`` is not defined.
The function will return a formatted path, but it might be picked randomly so reversing urls in such cases is highly
discouraged.

If you have access to :class:`request <.connection.Request>` instance you can make reverse lookups using
:meth:`url_for <.connection.ASGIConnection.url_for>` function which is similar to ``route_reverse`` but returns
absolute URL.


.. _handler_opts:

Adding arbitrary metadata to handlers
--------------------------------------

All route handler decorators accept a key called ``opt`` which accepts a dictionary of arbitrary values, e.g.

.. code-block:: python

   from litestar import get


   @get("/", opt={"my_key": "some-value"})
   def handler() -> None:
       ...

This dictionary can be accessed by a :doc:`route guard </usage/security/guards>`, or by accessing the ``route_handler``
property on a :class:`request <litestar.connection.request.Request>`, or using the
:class:`ASGI scope <litestar.types.Scope>` object directly.

Building on ``opts`` , you can pass any arbitrary kwarg to the route handler decorator, and it will be automatically set
as a key in the opt dictionary:

.. code-block:: python

   from litestar import get


   @get("/", my_key="some-value")
   def handler() -> None:
       ...


   assert handler.opt["my_key"] == "some-value"

You can specify the ``opt`` dictionary at all levels of your application. On specific route handlers, on a controller,
a router, and even on the app instance itself.

The resulting dictionary is constructed by merging opt dictionaries of all levels. If multiple layers define the same
key, the value from the closest layer to the response handler will take precedence.


.. _signature_namespace:

Signature namespace
-------------------

Litestar produces a model of the arguments to any handler or dependency function, called a "signature model" which is
used for parsing and validation of raw data to be injected into the function.

Building the model requires inspection of the names and types of the signature parameters at runtime, and so it is
necessary for the types to be available within the scope of the module - something that linting tools such as ``ruff``
or ``flake8-type-checking`` will actively monitor, and suggest against.

For example, the name ``Model`` is *not* available at runtime in the following snippet:

.. code-block:: python

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from litestar import Controller, post

    if TYPE_CHECKING:
        from domain import Model


    class MyController(Controller):
        @post()
        def create_item(data: Model) -> Model:
            return data


In this example, Litestar will be unable to generate the signature model because the type ``Model`` does not exist in
the module scope at runtime. We can address this on a case-by-case basis by silencing our linters, for example:

.. code-block:: python
    :no-upgrade:

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from litestar import Controller, post

    # Choose the appropriate noqa directive according to your linter
    from domain import Model  # noqa: TCH002

However, this approach can get tedious, so as an alternative, Litestar accepts a ``signature_types`` sequence at
every :ref:`layer <layered-architecture>` of the application. The following is a demonstration of how to use this
pattern.

This module defines our domain type in some central place.

.. literalinclude:: /examples/signature_namespace/domain.py
    :language: python

This module defines our controller, note that we don't import ``Model`` into the runtime namespace, nor do we require
any directives to control behavior of linters.

.. literalinclude:: /examples/signature_namespace/controller.py
    :language: python

Finally, we ensure that our application knows that when it encounters the name "Model" when parsing signatures, that it
should reference our domain ``Model`` type.

.. literalinclude:: /examples/signature_namespace/app.py
    :language: python

.. tip::

    If you want to map your type to a name that is different from its ``__name__`` attribute, you can use the
    ``signature_namespace`` parameter, e.g. ``app = Litestar(signature_namespace={"FooModel": Model})``.

    This enables import patterns like ``from domain.foo import Model as FooModel`` inside ``if TYPE_CHECKING`` blocks.

Default signature namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar automatically adds some names to the signature namespace when parsing signature models in order to support
injection of the :ref:`handler-function-kwargs`.

These names are:

* ``Headers``
* ``ImmutableState``
* ``Receive``
* ``Request``
* ``Scope``
* ``Send``
* ``State``
* ``WebSocket``
* ``WebSocketScope``

The import of any of these names can be safely left inside an ``if TYPE_CHECKING:`` block without any configuration
required.
