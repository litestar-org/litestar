
Creating Middleware
===================

As mentioned in :doc:`using middleware </usage/middleware/using-middleware>`, a middleware in Starlite
is **any callable** that takes a kwarg called ``app``, which is the next ASGI handler, i.e. an
:class:`ASGIApp <starlite.types.ASGIApp>`, and returns an ``ASGIApp``.

The example previously given was using a factory function, i.e.:

.. code-block:: python

   from starlite.types import ASGIApp, Scope, Receive, Send


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...
           await app(scope, receive, send)

       return my_middleware

While using functions is a perfectly viable approach, you can also use classes to do the same. See the next sections on
two base classes you can use for this purpose - the :class:`MiddlewareProtocol <.middleware.base.MiddlewareProtocol>` ,
which gives a bare-bones type, or the :class:`AbstractMiddleware <.middleware.base.AbstractMiddleware>` that offers a
base class with some built in functionality.

Using MiddlewareProtocol
------------------------

The :class:`MiddlewareProtocol <starlite.middleware.base.MiddlewareProtocol>` class is a
`PEP 544 Protocol <https://peps.python.org/pep-0544/>`_ that specifies the minimal implementation of a middleware as
follows:

.. code-block:: python

   from typing import Protocol, Any
   from starlite.types import ASGIApp, Scope, Receive, Send


   class MiddlewareProtocol(Protocol):
       def __init__(self, app: ASGIApp, **kwargs: Any) -> None: ...

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...

The ``__init__`` method receives and sets "app". *It's important to understand* that app is not an instance of Starlite in
this case, but rather the next middleware in the stack, which is also an ASGI app.

The ``__call__`` method makes this class into a ``callable``, i.e. once instantiated this class acts like a function, that
has the signature of an ASGI app: The three parameters, ``scope, receive, send`` are specified
by `the ASGI specification <https://asgi.readthedocs.io/en/latest/index.html>`_, and their values originate with the ASGI
server (e.g. *uvicorn*\ ) used to run Starlite.

To use this protocol as a basis, simply subclass it - as you would any other class, and implement the two methods it
specifies:

.. code-block:: python

   import logging

   from starlite.types import ASGIApp, Receive, Scope, Send
   from starlite import Request
   from starlite.middleware.base import MiddlewareProtocol

   logger = logging.getLogger(__name__)


   class MyRequestLoggingMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           super().__init__(app)
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               request = Request(scope)
               logger.info("%s - %s" % request.method, request.url)
           await self.app(scope, receive, send)

.. important::

    Although ``scope`` is used to create an instance of request by passing it to the
    :class:`Request <.connection.Request>` constructor, which makes it simpler to access because it does some parsing
    for you already, the actual source of truth remains ``scope`` - not the request. If you need to modify the data of
    the request you must modify the scope object, not any ephemeral request objects created as in the above.


Responding using the MiddlewareProtocol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once a middleware finishes doing whatever its doing, it should pass ``scope``, ``receive`` and ``send`` to an ASGI app
and await it. This is what's happening in the above example with: ``await self.app(scope, receive, send)``. Let's
explore another example - redirecting the request to a different url from a middleware:

.. code-block:: python

   from starlite.types import ASGIApp, Receive, Scope, Send

   from starlite.response import RedirectResponse
   from starlite import Request
   from starlite.middleware.base import MiddlewareProtocol


   class RedirectMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           super().__init__(app)
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if Request(scope).session is None:
               response = RedirectResponse(url="/login")
               await response(scope, receive, send)
           else:
               await self.app(scope, receive, send)

As you can see in the above, given some condition (request.session being None) we create a
:class:`RedirectResponse <starlite.response.RedirectResponse>` and then await it. Otherwise, we await ``self.app``


Modifying ASGI Requests and Responses using the MiddlewareProtocol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::

    If you'd like to modify a :class:`Response <.response.Response>` object after it was created for a route
    handler function but before the actual response message is transmitted, the correct place to do this is using the
    special life-cycle hook called :ref:`after_request <after_request>`. The instructions in this section are for how to
    modify the ASGI response message itself, which is a step further in the response process.

Using the :class:`MiddlewareProtocol <.middleware.base.MiddlewareProtocol>` you can intercept and modifying both the
incoming and outgoing data in a request / response cycle by "wrapping" that respective ``receive`` and ``send`` ASGI
functions.

To demonstrate this, lets say we want to append a header with a timestamp to all outgoing responses. We could achieve
this by doing the following:

.. code-block:: python

   import time

   from starlite.datastructures import MutableScopeHeaders
   from starlite.types import Message, Receive, Scope, Send
   from starlite.middleware.base import MiddlewareProtocol
   from starlite.types import ASGIApp


   class ProcessTimeHeader(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           super().__init__(app)
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               start_time = time.time()

               async def send_wrapper(message: Message) -> None:
                   if message["type"] == "http.response.start":
                       process_time = time.time() - start_time
                       headers = MutableScopeHeaders.from_message(message=message)
                       headers["X-Process-Time"] = str(process_time)
                   await send(message)

               await self.app(scope, receive, send_wrapper)
           else:
               await self.app(scope, receive, send)

Inheriting AbstractMiddleware
-----------------------------

Starlite offers an :class:`AbstractMiddleware <.middleware.base.AbstractMiddleware>` class that can be extended to
create middleware:

.. code-block:: python

   from typing import TYPE_CHECKING
   from time import time

   from starlite import AbstractMiddleware, ScopeType
   from starlite.datastructures import MutableScopeHeaders


   if TYPE_CHECKING:
       from starlite.types import Message, Receive, Scope, Send


   class MyMiddleware(AbstractMiddleware):
       scopes = {ScopeType.HTTP}
       exclude = ["first_path", "second_path"]
       exclude_opt_key = "exclude_from_middleware"

       async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
           start_time = time()

           async def send_wrapper(message: "Message") -> None:
               if message["type"] == "http.response.start":
                   process_time = time() - start_time
                   headers = MutableScopeHeaders.from_message(message=message)
                   headers["X-Process-Time"] = str(process_time)
                   await send(message)

           await self.app(scope, receive, send_wrapper)

The three class variables defined in the above example ``scopes``, ``exclude`` and ``exclude_opt_key`` can be used to
fine-tune for which routes and request types the middleware is called:


- The scopes variable is a set that can include either or both ``ScopeType.HTTP`` and ``ScopeType.WEBSOCKET`` , with the default being both.
- ``exclude`` accepts either a single string or list of strings that are compiled into a regex against which the request's ``path`` is checked.
- ``exclude_opt_key`` is the key to use for in a route handler's ``opt`` dict for a boolean, whether to omit from the middleware.

Thus, in the following example, the middleware will only run against the route handler called ``not_excluded_handler``:

.. literalinclude:: /examples/middleware/base.py
    :language: python



Using DefineMiddleware to pass arguments
----------------------------------------

Starlite offers a simple way to pass positional arguments (``*args``) and key-word arguments (``**kwargs``) to middleware
using the :class:`DefineMiddleware <starlite.middleware.base.DefineMiddleware>` class. Let's extend
the factory function used in the examples above to take some args and kwargs and then use ``DefineMiddleware`` to pass
these values to our middleware:

.. code-block:: python

   from starlite.types import ASGIApp, Scope, Receive, Send
   from starlite import Starlite, DefineMiddleware


   def middleware_factory(my_arg: int, *, app: ASGIApp, my_kwarg: str) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # here we can use my_arg and my_kwarg for some purpose
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Starlite(
       route_handlers=[...],
       middleware=[DefineMiddleware(middleware_factory, 1, my_kwarg="abc")],
   )

The ``DefineMiddleware`` is a simple container - it takes a middleware callable as a first parameter, and then any
positional arguments, followed by key word arguments. The middleware callable will be called with these values as well
as the kwarg ``app`` as mentioned above.
