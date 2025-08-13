Dependency Injection
====================

Litestar has a simple but powerful dependency injection system that allows for declaring dependencies on all layers of
the application:

.. code-block:: python

   from litestar import Controller, Router, Litestar, get
   from litestar.di import Provide


   async def bool_fn() -> bool: ...


   async def dict_fn() -> dict: ...


   async def list_fn() -> list: ...


   async def int_fn() -> int: ...


   class MyController(Controller):
       path = "/controller"
       # on the controller
       dependencies = {"controller_dependency": Provide(list_fn)}

       # on the route handler
       @get(path="/handler", dependencies={"local_dependency": Provide(int_fn)})
       def my_route_handler(
           self,
           app_dependency: bool,
           router_dependency: dict,
           controller_dependency: list,
           local_dependency: int,
       ) -> None: ...


   # on the router
   my_router = Router(
       path="/router",
       dependencies={"router_dependency": Provide(dict_fn)},
       route_handlers=[MyController],
   )

   # on the app
   app = Litestar(
       route_handlers=[my_router], dependencies={"app_dependency": Provide(bool_fn)}
   )

The above example illustrates how dependencies are declared on the different layers of the application.

.. note::

    Litestar needs the injected types at runtime which might clash with linter rules' recommendation to use ``TYPE_CHECKING``.

    .. seealso::

        :ref:`Signature namespace <signature_namespace>`

Dependencies can be either callables - sync or async functions, methods, or class instances that implement the
:meth:`object.__call__` method, or classes. These are in turn wrapped inside an instance of the
:class:`Provide <.di.Provide>` class.


.. include:: /admonitions/sync-to-thread-info.rst


Pre-requisites and scope
------------------------

The pre-requisites for dependency injection are these:


#. dependencies must be callables.
#. dependencies can receive kwargs and a ``self`` arg but not positional args.
#. the kwarg name and the dependency key must be identical.
#. the dependency must be declared using the ``Provide`` class.
#. the dependency must be in the *scope* of the handler function.

What is *scope* in this context? Dependencies are **isolated** to the context in which they are declared. Thus, in the
above example, the ``local_dependency`` can only be accessed within the specific route handler on which it was declared;
The ``controller_dependency`` is available only for route handlers on that specific controller; And the ``router
dependency`` is available only to the route handlers registered on that particular router. Only the ``app_dependency``
is available to all route handlers.

.. _yield_dependencies:

Dependencies with yield (cleanup step)
--------------------------------------

In addition to simple callables, dependencies can also be (async) generator functions, which allows
to execute an additional cleanup step, such as closing a connection, after the handler function
has returned.

.. admonition:: Technical details
    :class: info

    The cleanup stage is executed **after** the handler function returns, but **before** the
    response is sent (in case of HTTP requests)


A basic example
~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dependency_injection/dependency_yield_simple.py
    :caption: ``dependencies.py``
    :language: python


If you run the code you'll see that ``CONNECTION`` has been reset after the handler function
returned:

.. code-block:: python

   from litestar.testing import TestClient
   from dependencies import app, CONNECTION

   with TestClient(app=app) as client:
       print(client.get("/").json())  # {"open": True}
       print(CONNECTION)  # {"open": False}

Handling exceptions
~~~~~~~~~~~~~~~~~~~

If an exception occurs within the handler function, it will be raised **within** the
generator, at the point where it first ``yield`` ed. This makes it possible to adapt behaviour
of the dependency based on exceptions, for example rolling back a database session on error
and committing otherwise.

.. literalinclude:: /examples/dependency_injection/dependency_yield_exceptions.py
    :caption: ``dependencies.py``
    :language: python


.. code-block:: python

   from litestar.testing import TestClient
   from dependencies import STATE, app

   with TestClient(app=app) as client:
       response = client.get("/John")
       print(response.json())  # {"John": "hello"}
       print(STATE)  # {"result": "OK", "connection": "closed"}

       response = client.get("/Peter")
       print(response.status_code)  # 500
       print(STATE)  # {"result": "error", "connection": "closed"}


.. admonition:: Best Practice
    :class: tip

    You should always wrap ``yield`` in a ``try``/``finally`` block, regardless of
    whether you want to handle exceptions, to ensure that the cleanup code is run even
    when exceptions occurred:

    .. code-block:: python

        def generator_dependency():
            try:
                yield
            finally:
                ...  # cleanup code


.. attention::

    Do not re-raise exceptions within the dependency. Exceptions caught within these
    dependencies will still be handled by the regular mechanisms without an explicit
    re-raise


.. important::

    Exceptions raised during the cleanup step of a dependency will be re-raised in an
    :exc:`ExceptionGroup` (for Python versions < 3.11, the
    `exceptiongroup <https://github.com/agronholm/exceptiongroup>`_ will be used). This
    happens after all dependencies have been cleaned up, so exceptions raised during
    cleanup of one dependencies do not affect the cleanup of other dependencies.



Dependency keyword arguments
----------------------------

As stated above dependencies can receive kwargs but no args. The reason for this is that dependencies are parsed using
the same mechanism that parses route handler functions, and they too - like route handler functions, can have data
injected into them.

In fact, you can inject the same data that you
can :ref:`inject into route handlers <usage/routing/handlers:"reserved" keyword arguments>`.

.. code-block:: python

   from litestar import Controller, patch
   from litestar.di import Provide
   from pydantic import BaseModel, UUID4


   class User(BaseModel):
       id: UUID4
       name: str


   async def retrieve_db_user(user_id: UUID4) -> User: ...


   class UserController(Controller):
       path = "/user"
       dependencies = {"user": Provide(retrieve_db_user)}

       @patch(path="/{user_id:uuid}")
       async def get_user(self, user: User) -> User: ...

In the above example we have a ``User`` model that we are persisting into a db. The model is fetched using the helper
method ``retrieve_db_user`` which receives a ``user_id`` kwarg and retrieves the corresponding ``User`` instance.
The ``UserController`` class maps the ``retrieve_db_user`` provider to the key ``user`` in its ``dependencies`` dictionary. This
in turn makes it available as a kwarg in the ``get_user`` method.




Dependency overrides
--------------------

Because dependencies are declared at each level of the app using a string keyed dictionary, overriding dependencies is
very simple:

.. code-block:: python

   from litestar import Controller, get
   from litestar.di import Provide


   def bool_fn() -> bool: ...


   def dict_fn() -> dict: ...


   class MyController(Controller):
       path = "/controller"
       # on the controller
       dependencies = {"some_dependency": Provide(dict_fn)}

       # on the route handler
       @get(path="/handler", dependencies={"some_dependency": Provide(bool_fn)})
       def my_route_handler(
           self,
           some_dependency: bool,
       ) -> None: ...

The lower scoped route handler function declares a dependency with the same key as the one declared on the higher scoped
controller. The lower scoped dependency therefore overrides the higher scoped one.


The ``Provide`` class
----------------------

The :class:`Provide <.di.Provide>` class is a wrapper used for dependency injection. To inject a callable you must wrap
it in ``Provide``:

.. code-block:: python

   from random import randint
   from litestar import get
   from litestar.di import Provide


   def my_dependency() -> int:
       return randint(1, 10)


   @get(
       "/some-path",
       dependencies={
           "my_dep": Provide(
               my_dependency,
           )
       },
   )
   def my_handler(my_dep: int) -> None: ...


.. attention::

    If :class:`Provide.use_cache <.di.Provide>` is ``True``, the return value of the function will be memoized the first
    time it is called and then will be used. There is no sophisticated comparison of kwargs, LRU implementation, etc., so
    you should be careful when you choose to use this option. Note that dependencies will only be called once per
    request, even with ``Provide.use_cache`` set to ``False``.



Dependencies within dependencies
--------------------------------

You can inject dependencies into other dependencies - exactly like you would into regular functions.

.. code-block:: python

   from litestar import Litestar, get
   from litestar.di import Provide
   from random import randint


   def first_dependency() -> int:
       return randint(1, 10)


   def second_dependency(injected_integer: int) -> bool:
       return injected_integer % 2 == 0


   @get("/true-or-false")
   def true_or_false_handler(injected_bool: bool) -> str:
       return "its true!" if injected_bool else "nope, its false..."


   app = Litestar(
       route_handlers=[true_or_false_handler],
       dependencies={
           "injected_integer": Provide(first_dependency),
           "injected_bool": Provide(second_dependency),
       },
   )

.. note::

   The rules for `dependency overrides`_ apply here as well.


The ``Dependency`` function
----------------------------

Dependency validation
~~~~~~~~~~~~~~~~~~~~~

By default, injected dependency values are validated by Litestar, for example, this application will raise an
internal server error:

.. literalinclude:: /examples/dependency_injection/dependency_validation_error.py
    :caption: Dependency validation error
    :language: python


Dependency validation can be toggled using the :class:`Dependency <litestar.params.Dependency>` function.

.. literalinclude:: /examples/dependency_injection/dependency_skip_validation.py
    :caption: Dependency validation error
    :language: python


This may be useful for reasons of efficiency, or if pydantic cannot validate a certain type, but use with caution!

Dependency function as a marker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`Dependency <litestar.params.Dependency>` function can also be used as a marker that gives us a bit more detail
about your application.

Exclude dependencies with default values from OpenAPI docs
***********************************************************

Depending on your application design, it is possible to have a dependency declared in a handler or
:class:`Provide <.di.Provide>` function that has a default value. If the dependency isn't provided for the route, the
default should be used by the function.

.. literalinclude:: /examples/dependency_injection/dependency_with_default.py
    :caption: Dependency with default value
    :language: python


This doesn't fail, but due to the way the application determines parameter types, it is inferred to be a query
parameter.


By declaring the parameter to be a dependency, Litestar knows to exclude it from the docs:

.. literalinclude:: /examples/dependency_injection/dependency_with_dependency_fn_and_default.py
    :caption: Dependency with default value
    :language: python


Early detection if a dependency isn't provided
***********************************************

The other side of the same coin is when a dependency isn't provided, and no default is specified. Without the dependency
marker, the parameter is assumed to be a query parameter and the route will most likely fail when accessed.

If the parameter is marked as a dependency, this allows us to fail early instead:

.. literalinclude:: /examples/dependency_injection/dependency_non_optional_not_provided.py
   :caption: Dependency not provided error
   :language: python
