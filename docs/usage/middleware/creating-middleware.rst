Creating Middleware
===================

As mentioned in :ref:`using middleware <using-middleware>`, a middleware in Litestar
is **any callable** that takes a kwarg called ``app``, which is the next ASGI handler, i.e. an
:class:`~litestar.types.ASGIApp`, and returns an ``ASGIApp``.

The example previously given was using a factory function, i.e.:

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...
           await app(scope, receive, send)

       return my_middleware


Extending ``ASGIMiddleware``
----------------------------

While using functions is a perfectly viable approach, the recommended way to handle this
is by using the :class:`~litestar.middleware.ASGIMiddleware` abstract base class, which
also includes functionality to dynamically skip the middleware based on ASGI
``scope["type"]``, handler ``opt`` keys or path patterns and a simple way to pass
configuration to middlewares; It does not implement an ``__init__`` method, so
subclasses are free to use it to customize the middleware's configuration.


Modifying Requests and Responses
++++++++++++++++++++++++++++++++

Middlewares can not only be used to execute *around* other ASGI callable, they can also
intercept and modify both incoming and outgoing data in a request / response cycle by
"wrapping" the respective ``receive`` and ``send`` ASGI callables.

The following demonstrates how to add a request timing header with a timestamp to all
outgoing responses:

.. literalinclude:: /examples/middleware/request_timing.py
    :language: python


Configuration constraints
++++++++++++++++++++++++++

While it's good practice to keep middlewares decoupled from another, there are times
where implicit coupling is unavoidable due to the nature of the functionality provided
by the middlewares.

For example a caching middleware and an authentication middleware
can produce very different results depending on the order they are applied in; Assuming
a naive caching middleware that does not take authentication state into account, if it's
applied *before* the authentication middleware, it might cache an authenticated response
and serve it to the next, unauthenticated request.

Especially when applications grow larger and more complex, it can become difficult to
keep track of all these implicit couplings and dependencies, or downright impossible if
the middleware is implemented in a separate package and has no knowledge about how it is
being applied.

To help with this, :class:`~litestar.middleware.ASGIMiddleware` allows to specify a set
of :class:`~litestar.middleware.constraints.MiddlewareConstraints` - Once configured,
these will be validated on application startup.

Using constraints, the example given above might be solved like this:

.. literalinclude:: /examples/middleware/constraints.py
    :language: python

Here, we specify that every instance of ``CachingMiddleware`` must come after any
instance of
:class:`~litestar.middleware.authentication.AbstractAuthenticationMiddleware`.


.. tip::

    When referencing classes, the constraints always apply to all instances and
    subclasses of the type


Forward references
~~~~~~~~~~~~~~~~~~

Constraints that reference other middleware can use strings as forward references, to
handle situations like circular imports or middlewares from packages that may not be
available:

.. literalinclude:: /examples/middleware/constraints_string_ref.py
    :language: python

This forward reference will try to import ``SomeMiddleware`` from
``some_package.some_module``. With ``ignore_import_error=True``, if the import is not
successful, the constraint will be ignored.


Middleware order
~~~~~~~~~~~~~~~~

For order constraints (``before``, ``after``, ``first``, ``last``), it is important to
note that the order is defined in terms of proximity to the location. In practice, this
means that a middleware that has set ``first=True`` must be the *first* middleware on
the *first* layer (i.e. the application), and a middleware setting ``last=True`` must
be the *last* middleware on the *last* layer (i.e. the route handler).

.. code-block:: python

    @get("/", middleware=[FifthMiddleware, SixthMiddleware])
    async def handler() -> None:
        pass

    router = Router(
        "/",
        [handler],
        middleware=[
            ThirdMiddleware(),
            FourthMiddleware()
        ]
    )

    app = Litestar(
        middleware=[
            FirstMiddleware(),
            SecondMiddleware()
        ]
    )

Constraints and plugins
~~~~~~~~~~~~~~~~~~~~~~~

When using plugins that add middleware(s), it is important to understand that these
middleware(s) are added *after* middlewares defined on the application and *before* middlewares defined on the other layers.

Constraints are evaluated after all middlewares have been added though, so an order constraint on a middleware added by
a plugin has to take into account the position it is being added to.

Most of the time in a plugin you would do ``app_config.middleware.append(MyCustomMiddleware)`` which will be
ok if it has no constraints attached.

Now suppose that ``MyCustomMiddleware`` has the constraint ``first=True`` then the correct way to add it is to do
``app_config.middleware.insert(0, MyCustomMiddleware())`` so that it is the first middleware in the stack.


Migrating from ``MiddlewareProtocol`` / ``AbstractMiddleware``
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

:class:`~litestar.middleware.ASGIMiddleware` was introduced in Litestar 2.15. If you've
been using ``MiddlewareProtocol`` / ``AbstractMiddleware`` to implement your middlewares
before, there's a simple migration path to using ``ASGIMiddleware``.

**From MiddlewareProtocol**

.. tab-set::

    .. tab-item:: MiddlewareProtocol

        .. literalinclude:: /examples/middleware/middleware_protocol_migration_old.py
            :language: python

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/middleware_protocol_migration_new.py
            :language: python



**From AbstractMiddleware**

.. tab-set::

    .. tab-item:: MiddlewareProtocol

        .. literalinclude:: /examples/middleware/abstract_middleware_migration_old.py
            :language: python

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/abstract_middleware_migration_new.py
            :language: python






Using MiddlewareProtocol
------------------------

The :class:`~litestar.middleware.base.MiddlewareProtocol` class is a
`PEP 544 Protocol <https://peps.python.org/pep-0544/>`_ that specifies the minimal implementation of a middleware as
follows:

.. code-block:: python

   from typing import Protocol, Any
   from litestar.types import ASGIApp, Scope, Receive, Send


   class MiddlewareProtocol(Protocol):
       def __init__(self, app: ASGIApp, **kwargs: Any) -> None: ...

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...

The ``__init__`` method receives and sets "app". *It's important to understand* that app is not an instance of Litestar in
this case, but rather the next middleware in the stack, which is also an ASGI app.

The ``__call__`` method makes this class into a ``callable``, i.e. once instantiated this class acts like a function, that
has the signature of an ASGI app: The three parameters, ``scope, receive, send`` are specified
by `the ASGI specification <https://asgi.readthedocs.io/en/latest/index.html>`_, and their values originate with the ASGI
server (e.g. ``uvicorn``\ ) used to run Litestar.

To use this protocol as a basis, simply subclass it - as you would any other class, and implement the two methods it
specifies:

.. code-block:: python

   import logging

   from litestar.types import ASGIApp, Receive, Scope, Send
   from litestar import Request
   from litestar.middleware.base import MiddlewareProtocol

   logger = logging.getLogger(__name__)


   class MyRequestLoggingMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:  # can have other parameters as well
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               request = Request(scope)
               logger.info("Got request: %s - %s", request.method, request.url)
           await self.app(scope, receive, send)

.. important::

    Although ``scope`` is used to create an instance of request by passing it to the
    :class:`~litestar.connection.Request` constructor, which makes it simpler to access because it does some parsing
    for you already, the actual source of truth remains ``scope`` - not the request. If you need to modify the data of
    the request you must modify the scope object, not any ephemeral request objects created as in the above.


Responding using the MiddlewareProtocol
+++++++++++++++++++++++++++++++++++++++

Once a middleware finishes doing whatever its doing, it should pass ``scope``, ``receive``, and ``send`` to an ASGI app
and await it. This is what's happening in the above example with: ``await self.app(scope, receive, send)``. Let's
explore another example - redirecting the request to a different url from a middleware:

.. code-block:: python

   from litestar.types import ASGIApp, Receive, Scope, Send

   from litestar.response.redirect import ASGIRedirectResponse
   from litestar import Request
   from litestar.middleware.base import MiddlewareProtocol


   class RedirectMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if Request(scope).session is None:
               response = ASGIRedirectResponse(path="/login")
               await response(scope, receive, send)
           else:
               await self.app(scope, receive, send)

As you can see in the above, given some condition (``request.session`` being ``None``) we create a
:class:`~litestar.response.redirect.ASGIRedirectResponse` and then await it. Otherwise, we await ``self.app``

Modifying ASGI Requests and Responses using the MiddlewareProtocol
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. important::

    If you'd like to modify a :class:`~litestar.response.Response` object after it was created for a route
    handler function but before the actual response message is transmitted, the correct place to do this is using the
    special life-cycle hook called :ref:`after_request <after_request>`. The instructions in this section are for how to
    modify the ASGI response message itself, which is a step further in the response process.

Using the :class:`~litestar.middleware.base.MiddlewareProtocol` you can intercept and modifying both the
incoming and outgoing data in a request / response cycle by "wrapping" that respective ``receive`` and ``send`` ASGI
functions.

To demonstrate this, let's say we want to append a header with a timestamp to all outgoing responses. We could achieve
this by doing the following:

.. code-block:: python

   import time

   from litestar.datastructures import MutableScopeHeaders
   from litestar.types import Message, Receive, Scope, Send
   from litestar.middleware.base import MiddlewareProtocol
   from litestar.types import ASGIApp


   class ProcessTimeHeader(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           super().__init__(app)
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               start_time = time.monotonic()

               async def send_wrapper(message: Message) -> None:
                   if message["type"] == "http.response.start":
                       process_time = time.monotonic() - start_time
                       headers = MutableScopeHeaders.from_message(message=message)
                       headers["X-Process-Time"] = str(process_time)
                   await send(message)

               await self.app(scope, receive, send_wrapper)
           else:
               await self.app(scope, receive, send)

Inheriting AbstractMiddleware
-----------------------------

Litestar offers an :class:`~litestar.middleware.base.AbstractMiddleware` class that can be extended to
create middleware:

.. code-block:: python

   import time

   from litestar.enums import ScopeType
   from litestar.middleware import AbstractMiddleware
   from litestar.datastructures import MutableScopeHeaders
   from litestar.types import Message, Receive, Scope, Send


   class MyMiddleware(AbstractMiddleware):
       scopes = {ScopeType.HTTP}
       exclude = ["first_path", "second_path"]
       exclude_opt_key = "exclude_from_middleware"

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           start_time = time.monotonic()

           async def send_wrapper(message: "Message") -> None:
               if message["type"] == "http.response.start":
                   process_time = time.monotonic() - start_time
                   headers = MutableScopeHeaders.from_message(message=message)
                   headers["X-Process-Time"] = str(process_time)
               await send(message)

           await self.app(scope, receive, send_wrapper)

The three class variables defined in the above example ``scopes``, ``exclude``, and ``exclude_opt_key`` can be used to
fine-tune for which routes and request types the middleware is called:


- The scopes variable is a set that can include either or both : ``ScopeType.HTTP`` and ``ScopeType.WEBSOCKET`` , with the default being both.
- ``exclude`` accepts either a single string or list of strings that are compiled into a regex against which the request's ``path`` is checked.
- ``exclude_opt_key`` is the key to use for in a route handler's :class:`Router.opt <litestar.router.Router>` dict for a boolean, whether to omit from the middleware.

Thus, in the following example, the middleware will only run against the handler called ``not_excluded_handler`` for ``/greet`` route:

.. literalinclude:: /examples/middleware/base.py
    :language: python

.. danger::

    Using ``/`` as an exclude pattern, will disable this middleware for all routes,
    since, as a regex, it matches *every* path


Using DefineMiddleware to pass arguments
----------------------------------------

Litestar offers a simple way to pass positional arguments (``*args``) and keyword arguments (``**kwargs``) to middleware
using the :class:`~litestar.middleware.base.DefineMiddleware` class. Let's extend
the factory function used in the examples above to take some args and kwargs and then use ``DefineMiddleware`` to pass
these values to our middleware:

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send
   from litestar import Litestar
   from litestar.middleware import DefineMiddleware


   def middleware_factory(my_arg: int, *, app: ASGIApp, my_kwarg: str) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # here we can use my_arg and my_kwarg for some purpose
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Litestar(
       route_handlers=[...],
       middleware=[DefineMiddleware(middleware_factory, 1, my_kwarg="abc")],
   )

The ``DefineMiddleware`` is a simple container - it takes a middleware callable as a first parameter, and then any
positional arguments, followed by key word arguments. The middleware callable will be called with these values as well
as the kwarg ``app`` as mentioned above.
