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


Skipping the middleware
+++++++++++++++++++++++

The class variables ``scopes``, ``exclude_path_pattern`` and ``exclude_opt_key`` of
:class:`~litestar.middleware.ASGIMiddleware` can be used to fine-tune for which routes
and connection types the middleware is called:

- ``scopes`` is a tuple of the :class:`~litestar.enums.ScopeType` values the middleware
  applies to. It defaults to ``ScopeType.HTTP``, ``ScopeType.WEBSOCKET`` and
  ``ScopeType.ASGI``.
- ``exclude_path_pattern`` accepts a single string or a tuple of strings that are
  compiled into a regex, against which the path of each route handler is checked on
  application startup.
- ``exclude_opt_key`` is the key to use in a route handler's
  :class:`Router.opt <litestar.router.Router>` dict for a boolean, whether to omit the
  middleware.

Thus, in the following example, the middleware will only run against the handler called
``not_excluded_handler`` for the ``/greet`` route:

.. literalinclude:: /examples/middleware/base.py
    :language: python

.. danger::

    Using ``/`` as an exclude pattern, will disable this middleware for all routes,
    since, as a regex, it matches *every* path


.. _asgi-middleware-migration:

Migrating from ``MiddlewareProtocol``, ``AbstractMiddleware`` and ``DefineMiddleware``
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

``MiddlewareProtocol``, ``AbstractMiddleware`` and ``DefineMiddleware`` have been removed
in Litestar 3.0, in favour of :class:`~litestar.middleware.ASGIMiddleware`, which was
introduced in Litestar 2.15.

**From MiddlewareProtocol**

.. tab-set::

    .. tab-item:: MiddlewareProtocol

        .. code-block:: python

            from litestar.middleware import MiddlewareProtocol
            from litestar.types import ASGIApp, Receive, Scope, Send


            class MyMiddleware(MiddlewareProtocol):
                def __init__(self, app: ASGIApp) -> None:
                    self.app = app

                async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                    # do stuff
                    await self.app(scope, receive, send)

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/middleware_protocol_migration_new.py
            :language: python


**From AbstractMiddleware and DefineMiddleware**

.. tab-set::

    .. tab-item:: AbstractMiddleware

        .. code-block:: python

            import anyio

            from litestar import Litestar
            from litestar.middleware import AbstractMiddleware, DefineMiddleware
            from litestar.types import ASGIApp, Receive, Scope, Scopes, Send


            class TimeoutMiddleware(AbstractMiddleware):
                def __init__(
                    self,
                    app: ASGIApp,
                    timeout: float,
                    exclude: str | list[str] | None = None,
                    exclude_opt_key: str | None = None,
                    scopes: Scopes | None = None,
                ):
                    self.timeout = timeout
                    super().__init__(app=app, exclude=exclude, exclude_opt_key=exclude_opt_key, scopes=scopes)

                async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                    with anyio.move_on_after(self.timeout):
                        await self.app(scope, receive, send)


            app = Litestar(middleware=[DefineMiddleware(TimeoutMiddleware, timeout=5)])

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/abstract_middleware_migration_new.py
            :language: python

``AbstractMiddleware.exclude`` was matched against the request path on every request.
``ASGIMiddleware.exclude_path_pattern`` is matched against the handler's path once, on
application startup. To match the request path instead, set
:attr:`~litestar.middleware.ASGIMiddleware.should_bypass_for_scope`.

Middleware that isn't a class can keep using a factory function, binding its arguments
as described in :ref:`passing-arguments-to-middleware`.


.. _passing-arguments-to-middleware:

Passing arguments to middleware factories
-----------------------------------------

:class:`~litestar.middleware.ASGIMiddleware` subclasses receive their configuration
through their own ``__init__``. A factory function receives the next ASGI app as its
first argument; to pass it other arguments, bind them with :func:`functools.partial`:

.. code-block:: python

   from functools import partial

   from litestar import Litestar
   from litestar.types import ASGIApp, Receive, Scope, Send


   def middleware_factory(app: ASGIApp, my_arg: int, *, my_kwarg: str) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # here we can use my_arg and my_kwarg for some purpose
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Litestar(
       route_handlers=[...],
       middleware=[partial(middleware_factory, my_arg=1, my_kwarg="abc")],
   )
