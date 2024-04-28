Guards
======

Guards are callables that receive two arguments - ``connection``, which is the
:class:`ASGIConnection <.connection.ASGIConnection>` instance, and ``route_handler``, which is a copy of the
:class:`BaseRouteHandler <.handlers.BaseRouteHandler>`. Their role is to *authorize* the request by verifying that
the connection is allowed to reach the endpoint handler in question. If verification fails, the guard should raise an
HTTPException, usually a :class:`NotAuthorizedException <.exceptions.NotAuthorizedException>` with a ``status_code``
of 401.

To illustrate this we will implement a rudimentary role based authorization system in our Litestar app. As we have done
for ``authentication``, we will assume that we added some sort of persistence layer without actually
specifying it in the example.

We begin by creating an :class:`Enum <enum.Enum>` with two roles - ``consumer`` and ``admin``\ :

.. literalinclude:: /examples/guards/enum.py
    :language: python


Our ``User`` model will now look like this:

.. literalinclude:: /examples/guards/model.py
    :language: python


Given that the User model has a "role" property we can use it to authorize a request. Let's create a guard that only
allows admin users to access certain route handlers and then add it to a route handler function:

.. literalinclude:: /examples/guards/guard.py
    :language: python


Thus, only an admin user would be able to send a post request to the ``create_user`` handler.

Guard scopes
------------

Guards can be declared on all levels of the app - the Litestar instance, routers, controllers, and individual route
handlers:

.. literalinclude:: /examples/guards/guard_scope.py
    :language: python


The deciding factor on where to place a guard is on the kind of access restriction that are required: do only specific
route handlers need to be restricted? An entire controller? All the paths under a specific router? Or the entire app?

As you can see in the above examples - ``guards`` is a list. This means you can add **multiple** guards at every layer.
Unlike ``dependencies`` , guards do not override each other but are rather *cumulative*. This means that you can define
guards on different levels of your app, and they will combine.

.. caution::

    If guards are placed at the controller or the app level, they **will** be executed on all ``OPTIONS`` requests as well.
    For more details, including a workaround, refer https://github.com/litestar-org/litestar/issues/2314.


The route handler "opt" key
---------------------------

Occasionally there might be a need to set some values on the route handler itself - these can be permissions, or some
other flag. This can be achieved with :ref:`the opts kwarg <handler_opts>` of route handler

To illustrate this lets say we want to have an endpoint that is guarded by a "secret" token, to which end we create
the following guard:

.. literalinclude:: /examples/guards/route_handler.py
    :language: python
