Routing
=======

Starlite implements its routing solution that is based on the concept of a
`radix tree <https://en.wikipedia.org/wiki/Radix_tree>`_ or ``trie``.

Why Radix Based Routing?
------------------------

The regex matching used by Starlette (and FastAPI etc.) is very good at resolving path parameters fast, giving it
an advantage when a URL has a lot of path parameters - what we can think of as ``vertical`` scaling. On the
other hand, it is not good at scaling horizontally - the more routes, the less performant it becomes. Thus,
there is an inverse relation between performance and application size with this approach that strongly favors very
small microservices. The **trie** based approach used by Starlite is agnostic to the number of routes of the
application giving it better horizontal scaling characteristics at the expense of somewhat slower resolution of path
parameters.

.. seealso::

   If you are interested in the technical aspects of the implementation, refer to
   `this GitHub issue <https://github.com/starlite-api/starlite/issues/177>`_ - it includes
   an indepth discussion of the pertinent code.



Registering Routes
-------------------

At the root of every Starlite application there is an instance of the :class:`Starlite <starlite.app.Starlite>` class,
on which the root level controllers, routers and route handler functions are registered using the ``route_handlers`` kwarg:

.. code-block:: python

   from starlite import Starlite, get


   @get("/sub-path")
   def sub_path_handler() -> None: ...


   @get()
   def root_handler() -> None: ...


   app = Starlite(route_handlers=[root_handler, sub_path_handler])

Components registered on the app are appended to the root path. Thus, the ``root_handler`` function will be called for the
path ``"/"``, whereas the ``sub_path_handler`` will be called for ``"/sub-path"``. You can also declare a function to handle
multiple paths, e.g.:

.. code-block:: python

   from starlite import get, Starlite


   @get(["/", "/sub-path"])
   def handler() -> None: ...


   app = Starlite(route_handlers=[handler])

To handle more complex path schemas you should use `routers`_ and `controllers`_


Dynamic Route Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Occasionally there is a need for dynamic route registration. Starlite supports this via the ``.register`` method exposed
by the Starlite app instance:

.. code-block:: python

   from starlite import Starlite, get


   @get()
   def root_handler() -> None: ...


   app = Starlite(route_handlers=[root_handler])


   @get("/sub-path")
   def sub_path_handler() -> None: ...


   app.register(sub_path_handler)

Since the app instance is attached to all instances of :class:`ASGIConnection <.connection.base.ASGIConnection>`,
:class:`Request <.connection.request.Request>` and :class:`WebSocket <.connection.websocket.WebSocket>` objects, you can in
effect call the :meth:`register <.router.Router.register>` method inside route handler functions, middlewares and even
injected dependencies. For example:

.. code-block:: python

   from typing import Any
   from starlite import Starlite, Request, get


   @get("/some-path")
   def route_handler(request: Request[Any, Any]) -> None:
       @get("/sub-path")
       def sub_path_handler() -> None: ...

       request.app.register(sub_path_handler)


   app = Starlite(route_handlers=[route_handler])

In the above we dynamically created the sub-path_handler and registered it inside the ``route_handler`` function.

.. caution::

    Although Starlite exposes the :meth:`register <.router.Router.register>` method, it should not be abused. Dynamic
    route registration increases the application complexity and makes it harder to reason about the code. It should
    therefore be used only when absolutely required.


Routers
-------

Routers are instances of :class:`starlite.router.Router <.router.Router>`, which is the base class for the
:class:`Starlite app <.app.Starlite>` itself. A router can register Controllers, route handler functions and other routers,
similarly to the Starlite constructor:

.. code-block:: python

   from starlite import Starlite, Router, get


   @get("/{order_id:int}")
   def order_handler(order_id: int) -> None: ...


   order_router = Router(path="/orders", route_handlers=[order_handler])
   base_router = Router(path="/base", route_handlers=[order_router])
   app = Starlite(route_handlers=[base_router])

Once ``order_router`` is registered on ``base_router``\ , the handler function registered on ``order_router`` will
become available on ``/base/orders/{order_id}``.



Controllers
-----------

Controllers are subclasses of the class :class:`Controller <.controller.Controller>`. They are used to organize endpoints
under a specific sub-path, which is the controller's path. Their purpose is to allow users to utilize python OOP for
better code organization and organize code by logical concerns.

.. code-block:: python

   from pydantic import BaseModel, UUID4
   from starlite.controller import Controller
   from starlite.handlers import get, post, patch, delete
   from starlite.types import Partial


   class UserOrder(BaseModel):
       user_id: int
       order: str


   class UserOrderController(Controller):
       path = "/user-order"

       @post()
       async def create_user_order(self, data: UserOrder) -> UserOrder: ...

       @get(path="/{order_id:uuid}")
       async def retrieve_user_order(self, order_id: UUID4) -> UserOrder: ...

       @patch(path="/{order_id:uuid}")
       async def update_user_order(
           self, order_id: UUID4, data: Partial[UserOrder]
       ) -> UserOrder: ...

       @delete(path="/{order_id:uuid}")
       async def delete_user_order(self, order_id: UUID4) -> None: ...

The above is a simple example of a "CRUD" controller for a model called ``UserOrder``. You can place as
many `route handler methods <usage/router-handlers:http route handlers>`_ on a controller,
as long as the combination of path+http method is unique.

The ``path`` that is defined on the Controller is appended before the path that is defined for the route handlers declared
on it. Thus, in the above example, ``create_user_order`` has the path of the controller - ``/user-order/`` ,
while ``retrieve_user_order`` has the path ``/user-order/{order_id:uuid}"``.

.. note::

    If you do not declare a ``path`` class variable on the controller, it will default to the root path of ``"/"``.



Registering components multiple times
--------------------------------------

You can register both standalone route handler functions and controllers multiple times.

Registering controllers multiple times
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from starlite import Router, Controller, get


   class MyController(Controller):
       path = "/controller"

       @get()
       def handler(self) -> None: ...


   internal_router = Router(path="/internal", route_handlers=[MyController])
   partner_router = Router(path="/partner", route_handlers=[MyController])
   consumer_router = Router(path="/consumer", route_handlers=[MyController])

In the above, the same ``MyController`` class has been registered on three different routers. This is possible because
what is passed to the router is not a class instance but rather the class itself. The router creates its own instance of
the controller, which ensures encapsulation.

Therefore, in the above example, three different instances of ``MyController`` will be created, each mounted on a
different sub-path, e.g. ``/internal/controller``\ , ``/partner/controller`` and ``/consumer/controller``.

Registering standalone route handlers multiple times
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also register standalone route handlers multiple times:

.. code-block:: python

   from starlite import Starlite, Router, get


   @get(path="/handler")
   def my_route_handler() -> None: ...


   internal_router = Router(path="/internal", route_handlers=[my_route_handler])
   partner_router = Router(path="/partner", route_handlers=[my_route_handler])
   consumer_router = Router(path="/consumer", route_handlers=[my_route_handler])

   Starlite(route_handlers=[internal_router, partner_router, consumer_router])

When the handler function is registered, it's actually copied. Thus, each router has its own unique instance of
the route handler. Path behaviour is identical to that of controllers above, namely, the route handler
function will be accessible in the following paths: ``/internal/handler`` , ``/partner/handler`` and ``/consumer/handler``.

.. attention::

   You can nest routers as you see fit - but be aware that once a router has been registered it cannot be
   re-registered or an exception will be raised.



Mounting ASGI Apps
-------------------

Starlite support "mounting" ASGI applications on sub paths, that is - specifying a handler function that will handle all
requests addressed to a given path.

.. literalinclude:: /examples/routing/mount_custom_app.py
    :caption: Mounting an ASGI App
    :language: python


The handler function will receive all requests with an url that begins with ``/some/sub-path`` , e.g. ``/some/sub-path`` and
``/some/sub-path/abc`` and ``/some/sub-path/123/another/sub-path`` etc.

.. admonition:: Technical Details
    :class: info

    If we are sending a request to the above with the url ``/some/sub-path``, the handler will be invoked and
    the value of ``scope["path"]`` will equal ``"/`"``. If we send a request to ``/some/sub-path/abc``, it will also be
    invoked,and ``scope["path"]`` will equal ``"/abc"``.

Mounting is especially useful when you need to combine components of other ASGI applications - for example, for 3rd part libraries.
The following example is identical in principle to the one above, but it uses `Starlette <https://www.starlette.io/>`_:

.. literalinclude:: /examples/routing/mounting_starlette_app.py
   :caption: Mounting a Starlette App
   :language: python
