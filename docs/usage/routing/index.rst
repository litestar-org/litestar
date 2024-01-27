Routing
=======

Litestar's routing system is based around a few basic components:

Route handlers
    Callables that receive parameters from the request or dependencies and return
    response data

Controllers
    Classes that group together multiple route handlers and define common attributes
    such as dependencies and middlewares

Routers
    A lightweight application on which route handlers, controllers and other routers can
    be registered, as well as common configurations such as dependencies and middlewares

Applications
    Instances of :class:`~litestar.app.Litestar`, a special type of router that serves
    as the entry point of an application, in addition to receive the same configuration
    routers can


With the exception of applications, these components can be arbitrarily nested and
combined as long as they ultimately define a path that starts with an application and
ends with a route handler, allowing to organize complex routing tables into logical
groups.



Component registration
----------------------

Components are registered by passing them to their containing layer:

.. literalinclude:: /examples/routing/registration_1.py
    :language: python



In this example, a route handler is registered directly with the application. The same
can be done with a router

.. literalinclude:: /examples/routing/registration_2.py
    :language: python


and registering a router works in the same way as well:

.. literalinclude:: /examples/routing/registration_3.py
    :language: python


just like registering a controller does:

.. literalinclude:: /examples/routing/registration_4.py
    :language: python


Registering components dynamically
++++++++++++++++++++++++++++++++++

It is possible to register components dynamically on a :class:`~litestar.app.Litestar`
or :class:`~litestar.router.Router` instance by making use of the
:meth:`~litestar.router.Router.register` method:

.. literalinclude:: /examples/routing/dynamic_registration.py
    :language: python


.. attention::
    It is generally advised to only use this pattern if strictly necessary. In most
    cases it is possible to work around this by using plugins or the factory pattern.


Reusing handlers and controllers under different paths
++++++++++++++++++++++++++++++++++++++++++++++++++++++

Route handlers and controllers can be registered multiple times under different paths:

.. tab-set::

    .. tab-item:: Handler

        .. literalinclude:: /examples/routing/reusing_1.py
            :language: python

    .. tab-item:: Controller

        .. literalinclude:: /examples/routing/reusing_2.py
            :language: python


Defining paths
--------------

Every component can define its path, that is, the part of the HTTP request's URL the
component should respond to. Paths are organized hierarchically, with every component
using the path of its ancestor as its base path. In practice this means that a route
handler with the path ``/handler`` registered on a router with the path ``/router``
will be respond to the path ``/router/handler``.

Handlers
++++++++

On a route handler, that path can be set using the ``path`` argument:

.. tab-set::

    .. tab-item:: Positional

        .. literalinclude:: /examples/routing/handler_path_positional.py
            :language: python

    .. tab-item:: Keyword

        .. literalinclude:: /examples/routing/handler_path_kwarg.py
            :language: python


When not provided, the path defaults to ``/``.


Controllers
+++++++++++

The path on a controller can be set with the ``path`` attribute:

.. literalinclude:: /examples/routing/controller_path.py
    :language: python


When not provided, the path defaults to ``/``.

Routers
+++++++

The path on a router can be set via the ``path`` argument. Unlike handlers and
controllers, specifying a path is not optional.

.. literalinclude:: /examples/routing/router_path.py
    :language: python


Setting a base path for the application
++++++++++++++++++++++++++++++++++++++++

Sometimes it is desirable to set a base path for the entire application. While it is
generally advisable to handle this outside the application itself (e.g. via a reverse
proxy), this can be achieved by registering all route handlers with a router, and
setting the base path there.


Dynamic paths with path parameters
++++++++++++++++++++++++++++++++++

Dynamic paths can be created with the help of path parameters. These are part of the
path string and follow the basic form of ``{<parameter name>:<parameter type>}``, where
``<parameter name>`` is the name of the parameter used to make its value available to
the route handler and what will be represented in the OpenAPI schema, and
``<parameter type>`` a basic Python type that this parameter will be validated against
and, if possible, converted to.

.. literalinclude:: /examples/routing/path_parameters_1.py


.. important::
    If the conversion fails, the path will be considered a non-match, and a
    ``404 - Not Found`` response will be returned


Supported types
***************


str
    Accepts all strings, excluding those with path separators

int
    Accepts ints and converts them into an :class:`int`

float
    Accepts ints and floats and converts them into a :class:`float`

decimal
    Accepts decimal values and floats and converts them into a :class:`decimal.Decimal`

path
    Accepts all strings, including those with path separators. Values are passed
    unchanged to the route handler

date
    Accepts date strings in ISO 8601 format and UNIX timestamps and converts them into a
    :class:`datetime.date`

time
    Accepts time strings in ISO 8601 format and converts them into a
    :class:`datetime.time`

datetime
    Accepts datetime strings in ISO 8601 format and UNIX timestamps and converts them
    into a :class:`datetime.datetime`

timedelta
    Accepts time duration strings in ISO 8601 format and converts them into a
    :class:`datetime.timedelta`

uuid
    Accepts UUID strings according to RFC4122 and converts them into a
    :class:`uuid.UUID`

..
    Explain difference between the type coercion and validation here
    Add backlink to "data validation / parsing" chapter


Path parameters on higher layers
********************************

Path parameters can be set on all components that allow to define paths, following the
same semantics as for route handlers:

.. literalinclude:: /examples/routing/layered_path_parameters.py
    :language: python



Handling multiple HTTP methods on the same path
-----------------------------------------------

Responding to different HTTP methods on the same path can be done in two ways:

- Setting up dedicated route handlers for each method
- Using the :class:`~litestar.handlers.route` decorator to handle multiple methods
  within the same handler


Sharing a path between route handlers
++++++++++++++++++++++++++++++++++++++

Route handlers can share a path, as long as long as their HTTP methods are distinct, so
the best way to handle multiple methods on the same path is setting up explicit route
handlers for them:

.. literalinclude:: /examples/routing/multi_methods_multi_handlers.py
    :language: python


Handling multiple methods within the same handler
++++++++++++++++++++++++++++++++++++++++++++++++++

Alternatively, a single route handler can be used to handle multiple methods, making use
of the :class:`~litestar.handlers.route` decorator, and the
:attr:`Request.method <litestar.connection.Request.method>` property to check the method
used for the current request:

.. literalinclude:: /examples/routing/multi_methods_single_handler.py
    :language: python



Mounting ASGI applications
--------------------------

An :class:`~litestar.handlers.asgi` handler can be used to forward requests to other
ASGI applications ("mounting" them):

.. tab-set::

    .. tab-item:: Functional

        .. literalinclude:: /examples/routing/mounting_functional.py
            :language: python

    .. tab-item:: Explicit

        .. literalinclude:: /examples/routing/mounting_explicit.py
            :language: python

.. attention::
    ASGI mounts are "catch all" by default; They will match all HTTP methods and
    sub-paths of the base path they define

.. admonition:: Request paths in mounted applications

    The path received by the mounted aplication will be the first part of the path that
    was not consumed by handler, so in the above example, a request to
    ``/some/sub-path`` would be received as ``/`` by the mounted app, and a request to
    ``/some/sub-path/index`` would be received as ``/index``.

    This ensures that the mounted application does not need any knowledge about being
    mounted to function properly.


Creating a catch-all handler
----------------------------


There is no built-in catch-all handler, but one can easily be constructed using the
``path`` type path parameter:

.. literalinclude:: /examples/routing/catchall_handler.py
    :language: python

This handler will match all ``GET`` requests for all paths. If in addition to all paths,
all methods should be matched as well, this can be achieved with the
:class:`~litestar.handlers.route` handler decorator, which can match multiple HTTP
methods.

.. literalinclude:: /examples/routing/catchall_handler_all_methods.py
    :language: python





Route handlers
--------------
..
    Move to reference section?


- :class:`~litestar.handlers.get` to handle HTTP ``GET`` requests
- :class:`~litestar.handlers.post` to handle HTTP ``POST`` requests
- :class:`~litestar.handlers.patch` to handle HTTP ``PATCH`` requests
- :class:`~litestar.handlers.put` to handle HTTP ``PUT`` requests
- :class:`~litestar.handlers.delete` to handle HTTP ``DELETE`` requests
- :class:`~litestar.handlers.head` to handle HTTP ``HEAD`` requests
- :class:`~litestar.handlers.route` to handle multiple HTTP methods
- :class:`~litestar.handlers.asgi` to dispatch ASGI applications
- :class:`~litestar.handlers.websocket` to handle WebSocket connections



HTTP
++++

TBD


WebSocket
+++++++++

TBD


ASGI
++++

TBD


Controllers
-----------

..
    Move to reference section?

Controllers are classes that inherit from :class:`~litestar.controller.Controller`


TBD


Routers
-------
..
    Move to reference section?

TBD


Shared configuration
--------------------

..
   Find a better place for this

All components share a subset of their configuration, allowing for a layered
architecture in which components on a lower layer inherit the configuration of the
layers above them, thereby enabling to scope specific configurations to the
application's needs.

Configuration shared by all components are:

- dependencies
- after_request
- after_response
- before_request
- cache_control
- dto
- return_dto
- etag
- exception_handlers
- guards
- middleware
- opt
- response_class
- response_headers
- response_cookies
- signature_namespace
- signature_types
- type_encoders
- type_decoders

..
   Add links here


A special case is the ``path``, which is available on all layers, instead of being
inherited is used as the base path for subcomponents.

