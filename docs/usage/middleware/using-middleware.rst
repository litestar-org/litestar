.. _using-middleware:

Using Middleware
================

A middleware in Litestar is any callable that receives at least one kwarg called ``app`` and returns an
:class:`ASGIApp <litestar.types.ASGIApp>`. An ``ASGIApp`` is nothing but an async function that receives the ASGI
primitives ``scope`` , ``receive`` and ``send`` , and either calls the next ``ASGIApp`` or returns a response / handles
the websocket connection.

For example, the following function can be used as a middleware because it receives the ``app`` kwarg and returns
an ``ASGIApp``:

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...
           await app(scope, receive, send)

       return my_middleware

We can then pass this middleware to the :class:`Litestar <.app.Litestar>` instance, where it will be called on
every request:

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send
   from litestar import Litestar


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # do something here
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Litestar(route_handlers=[...], middleware=[middleware_factory])

In the above example, Litestar will call the ``middleware_factory`` function and pass to it ``app``. It's important to
understand that this kwarg does not designate the Litestar application but rather the next ``ASGIApp`` in the stack. It
will then insert the returned ``my_middleware`` function into the stack of every route in the application -
because we declared it on the application level.

.. admonition::  Layered architecture
    :class: seealso

    Middlewares are part of Litestar's layered architecture* which means you can
    set them on every layer of the application.

    You can read more about this here: :ref:`usage/applications:layered architecture`


Middleware Call Order
---------------------

Since it's also possible to define multiple middlewares on every layer, the call order for
middlewares will be **top to bottom** and **left to right**. This means for each layer, the
middlewares will be called in the order they have been passed, while the layers will be
traversed in the usual order:

.. mermaid::

   flowchart LR
       Application --> Router --> Controller --> Handler


.. literalinclude:: /examples/middleware/call_order.py
    :language: python



Middlewares and Exceptions
--------------------------

When an exception is raised by a route handler or a :doc:`dependency </usage/dependency-injection>`
it will be transformed into a response by an :ref:`exception handler <usage/exceptions:exception handling>`.
This response will follow the normal "flow" of the application and therefore, middlewares are
still applied to it.

As with any good rule, there are exceptions to it. In this case they are two exceptions
raised by Litestar's ASGI router:


* :class:`NotFoundException <litestar.exceptions.http_exceptions.NotFoundException>`
* :class:`MethodNotAllowedException <litestar.exceptions.http_exceptions.MethodNotAllowedException>`

They are raised **before the middleware stack is called** and will only be handled by exception
handlers defined on the ``Litestar`` instance itself. If you wish to modify error responses generated
from these exception, you will have to use an application layer exception handler.
