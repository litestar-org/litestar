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

due to the way we're traversing over the app layers, the middleware stack is
constructed in 'application > handler' order, which is the order we want the
middleware to be called in.

using this order however, since each middleware wraps the next callable, the
*first* middleware in the stack would up being the *innermost* wrapper, i.e.
the last one to receive the request and the first one to see the response.

to achieve the intended call order, we perform the wrapping in reverse
('handler -> application').


.. mermaid::

    graph TD
        request --> M1
        M1 --> M2
        M2 --> H
        H --> M2R
        M2R --> M1R
        M1R --> response

        subgraph M1 [middleware_1]
            M2
            subgraph M2 [middleware_2]
                H[handler]
            end
        end

        style M1 stroke:#333,stroke-width:2px
        style M2 stroke:#555,stroke-width:1.5px
        style H stroke:#777,stroke-width:1px



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
