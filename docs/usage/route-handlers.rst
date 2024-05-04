Route handlers
==============

Route handlers are the core of Starlite. They are constructed by decorating a function or class method with one of the
handler decorators exported from Starlite.

For example:

.. code-block:: python

   from starlite import MediaType, get


   @get("/", media_type=MediaType.TEXT)
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

Declaring path(s)
-----------------

All route handler decorator accept an optional path argument. This argument can be declared as a kwarg using the ``path``
key word:

.. code-block:: python

   from starlite import get


   @get(path="/some-path")
   def my_route_handler() -> None: ...

It can also be passed as an argument without the key-word:

.. code-block:: python

   from starlite import get


   @get("/some-path")
   def my_route_handler() -> None: ...

And the value for this argument can be either a string path, as in the above examples, or a list of string paths:

.. code-block:: python

   from starlite import get


   @get(["/some-path", "/some-other-path"])
   def my_route_handler() -> None: ...

This is particularly useful when you want to have optional :ref:`path parameters <usage/parameters:Path Parameters>`:

.. code-block:: python

   from starlite import get


   @get(
       ["/some-path", "/some-path/{some_id:int}"],
   )
   def my_route_handler(some_id: int = 1) -> None: ...

Handler function kwargs
-----------------------

Route handler functions or methods access various data by declaring these as annotated function kwargs. The annotated
kwargs are inspected by Starlite and then injected into the request handler.

The following sources can be accessed using annotated function kwargs:

- :ref:`path, query, header and cookie parameters <usage/parameters:the parameter function>`
- :doc:`/usage/request-data`
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
   from starlite import State, Request, get
   from starlite.datastructures import Headers


   @get(path="/")
   def my_request_handler(
       state: State,
       request: Request,
       headers: Headers,
       query: Dict[str, Any],
       cookies: Dict[str, Any],
   ) -> None: ...

.. tip::

    You can define a custom typing for your application state and then use it as a type instead of just using the
    State class from Starlite

Handler function type annotations
---------------------------------

Starlite enforces strict type annotations. Functions decorated by a route handler **must** have all their kwargs and
return value type annotated. If a type annotation is missing, an
:class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>` will be raised during the
application boot-up process.

There are several reasons for why this limitation is enforced:


#. to ensure best practices
#. to ensure consistent OpenAPI schema generation
#. to allow Starlite to compute during the application bootstrap all the kwargs required by a function


HTTP route handlers
-------------------

The most commonly used route handlers are those that handle http requests and responses. These route handlers all
inherit from the class :class:`HTTPRouteHandler <starlite.handlers.http.HTTPRouteHandler>`, which
is aliased as the decorator called :func:`route <starlite.handlers.route>`:

.. code-block:: python

   from starlite import HttpMethod, route


   @route(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
   def my_endpoint() -> None: ...

As mentioned above, ``route`` does is merely an alias for ``HTTPRouteHandler``\ , thus the below code is equivalent to the one
above:

.. code-block:: python

   from starlite import HttpMethod, HTTPRouteHandler


   @HTTPRouteHandler(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
   def my_endpoint() -> None: ...

HTTP route handlers kwargs
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``route`` decorator **requires** an ``http_method`` kwarg, which is a member of the
:class:`HttpMethod <.enums.HttpMethod>` enum or a list of members, e.g. ``HttpMethod.GET`` or
``[HttpMethod.PATCH, HttpMethod.PUT]``.


Semantic handler decorators
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starlite also includes "semantic" decorators, that is, decorators the pre-set the ``http_method`` kwarg to a specific HTTP
verb, which correlates with their name:


* :func:`delete <starlite.handlers.delete>`
* :func:`get <starlite.handlers.get>`
* :func:`head <starlite.handlers.head>`
* :func:`patch <starlite.handlers.patch>`
* :func:`post <starlite.handlers.post>`
* :func:`put <starlite.handlers.put>`

These are used exactly like ``route`` with the sole exception that you cannot configure the ``http_method`` kwarg:

.. code-block:: python

   from starlite import Partial, delete, get, patch, post, put, head
   from pydantic import BaseModel


   class Resource(BaseModel): ...


   @get(path="/resources")
   def list_resources() -> list[Resource]: ...


   @post(path="/resources")
   def create_resource(data: Resource) -> Resource: ...


   @get(path="/resources/{pk:int}")
   def retrieve_resource(pk: int) -> Resource: ...


   @head(path="/resources/{pk:int}")
   def retrieve_resource_head(pk: int) -> None: ...


   @put(path="/resources/{pk:int}")
   def update_resource(data: Resource, pk: int) -> Resource: ...


   @patch(path="/resources/{pk:int}")
   def partially_update_resource(data: Partial[Resource], pk: int) -> Resource: ...


   @delete(path="/resources/{pk:int}")
   def delete_resource(pk: int) -> None: ...

Although these decorators are merely subclasses of :class:`HTTPRouteHandler <starlite.handlers.http.HTTPRouteHandler>`
that pre-set the ``http_method``\ , using *get*\ , *patch*\ , *put*\ , *delete* or *post* instead of *route* makes the
code clearer and simpler.

Furthermore, in the OpenAPI specification each unique combination of http verb (e.g. "GET", "POST" etc.) and path is
regarded as a distinct `operation <https://spec.openapis.org/oas/latest.html#operation-object>`_\ , and each operation
should be distinguished by a unique ``operationId`` and optimally also have a ``summary`` and ``description`` sections.

As such, using the ``route`` decorator is discouraged. Instead, the preferred pattern is to share code using secondary
class methods or by abstracting code to reusable functions.

Using sync handler functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use both sync and async functions as the base for route handler functions, but which should you use? and when?

If your route handler needs to perform an I/O operation (read or write data from or to a service / db etc.), the most
performant solution within the scope of an ASGI application, including Starlite, is going to be by using an async
solution for this purpose.

The reason for this is that async code, if written correctly, is **non-blocking**. That is, async code can be paused and
resumed, and it therefore does not interrupt the main event loop from executing (if written correctly). On the other
hand, sync I/O handling is often **blocking**\ , and if you use such code in your function it can create performance
issues.

In this case you should use the ``sync_to_thread`` option. What this does, is tell Starlite to run the sync function in a
separate async thread, where it can block but will not interrupt the main event loop's execution.

The problem with this though is that this will slow down the execution of your sync code quite dramatically - by between
%40-60%. So this is really quite far from performant. Thus, you should use this option **only** when your sync code
performs blocking I/O operations. If your sync code simply performs simple tasks, non-expensive calculations, etc. you
should not use the ``sync_to_thread`` option.



Websocket route handlers
------------------------

Starlite supports Websockets via the :func:`websocket <starlite.handlers.websocket>` decorator:

.. code-block:: python

   from starlite import WebSocket, websocket


   @websocket(path="/socket")
   async def my_websocket_handler(socket: WebSocket) -> None:
       await socket.accept()
       await socket.send_json({...})
       await socket.close()

The\ ``websocket`` decorator is an alias of the class
:class:`WebsocketRouteHandler <starlite.handlers.websocket.WebsocketRouteHandler>`. Thus, the below
code is equivalent to the one above:

.. code-block:: python

   from starlite import WebSocket, WebsocketRouteHandler


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

See the :class:`API Reference <starlite.handlers.WebsocketRouteHandler>` for full details on the ``websocket`` decorator and the kwargs it accepts.


ASGI route handlers
-------------------

If you need to write your own ASGI application, you can do so using the :func:`asgi <starlite.handlers.asgi>` decorator:

.. code-block:: python

   from starlite.types import Scope, Receive, Send
   from starlite.status_codes import HTTP_400_BAD_REQUEST
   from starlite import Response, asgi


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
:class:`ASGIRouteHandler <.handlers.asgi.ASGIRouteHandler>`. Thus,
the code below is equivalent to the one above:

.. code-block:: python

   from starlite.types import Scope, Receive, Send
   from starlite.status_codes import HTTP_400_BAD_REQUEST
   from starlite import ASGIRouteHandler, Response


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

See the :class:`API Reference <starlite.handlers.ASGIRouteHandler>` for full details on the ``asgi`` decorator and the
kwargs it accepts.



Route handler indexing
----------------------

You can provide in all route handler decorators a ``name`` kwarg. The value for this kwarg **must be unique**\ , otherwise
:class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>` exception will be raised. Default
value for ``name`` is value returned by ``handler.__str__`` which should be the full dotted path to the handler
(e.g. ``app.controllers.projects.list`` for ``list`` function residing in ``app/controllers/projects.py`` file). ``name`` can
be used to dynamically retrieve (i.e. during runtime) a mapping containing the route handler instance and paths, also
it can be used to build a URL path for that handler:

.. code-block:: python

   from starlite import Starlite, Request, Redirect, NotFoundException, get


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


   app = Starlite(route_handlers=[handler_one, handler_two, handler_three])

:meth:`route_reverse <.app.Starlite.route_reverse>` will raise
:class:`NoMatchRouteFoundException <.exceptions.NoRouteMatchFoundException>` if route with given name was not found
or if any of path parameters is missing or if any of passed path parameters types do not match types in the respective
route declaration. However, :class:`str` is accepted in place of :class:`datetime.datetime`, :class:`datetime.date`,
:class:`datetime.time`, :class:`datetime.timedelta`, :class:`float`, and :class:`pathlib.Path`
parameters, so you can apply custom formatting and pass the result to ``route_reverse``.

If handler has multiple paths attached to it ``route_reverse`` will return the path that consumes the most number of
keywords arguments passed to the function.

.. code-block:: python

   from starlite import get, Request


   @get(
       ["/some-path", "/some-path/{id:int}", "/some-path/{id:int}/{val:str}"],
       name="handler_name",
   )
   def handler(id: int = 1, val: str = "default") -> None: ...


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

If you have access to :class:`request <starlite.connection.request.Request>` instance you can make reverse lookups using
:meth:`url_for <.connection.base.ASGIConnection.url_for>` function which is similar to ``route_reverse`` but returns
absolute URL.


.. _handler_opts:

Handler ``opts``
----------------

All route handler decorators accept a key called ``opt`` which accepts a dictionary of arbitrary values, e.g.

.. code-block:: python

   from starlite import get


   @get("/", opt={"my_key": "some-value"})
   def handler() -> None: ...

This dictionary can be accessed by a :doc:`route guard </usage/security/guards>`, or by accessing the ``route_handler``
property on a :class:`request <starlite.connection.request.Request>`, or using the
:class:`ASGI scope <starlite.types.Scope>` object directly.

Passing keyword arguments to handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Building on ``opts`` , you can pass any arbitrary kwarg to the route handler decorator, and it will be automatically set
as a key in the opt dictionary:

.. code-block:: python

   from starlite import get


   @get("/", my_key="some-value")
   def handler() -> None: ...


   assert handler.opt["my_key"] == "some-value"

You can specify the ``opt`` dictionary at all levels of your application. On specific route handlers, on a controller,
a router, and even on the app instance itself.

The resulting dictionary is constructed by merging opt dictionaries of all levels. If multiple layers define the same
key, the value from the closest layer to the response handler will take precedence.
