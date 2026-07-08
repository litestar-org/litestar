Recap and assembling the final application
===========================================

So far we have looked at the different parts of the application in isolation, but now
it's time to put them all together and assemble a complete application.


Final application
-----------------

.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :linenos:


Recap
-----


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 29-33
    :lineno-start: 29


A route handler set up with ``get("/")`` responds to ``GET`` requests and returns a list
of all items on our TODO list. The optional query parameter ``done`` allows filtering
the items by status. It is declared as ``FromQuery[bool | None]``: the
:data:`~.params.FromQuery` marker tells Litestar to read the value from the URL query
string, the inner ``bool`` triggers conversion, and wrapping it in
:class:`Optional <typing.Optional>` (combined with the ``= None`` default) makes it
optional.


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 36-39
    :lineno-start: 36


A route handler set up with ``post("/")`` responds to ``POST`` requests and adds an item
to the TODO list. The data for the new item is received via the request data, which the
route handler accesses by specifying the ``data`` parameter. The type annotation of
``TodoItem`` means the request data will parsed as JSON, which is then used to create an
instance of the ``TodoItem`` dataclass, which - finally - gets passed into the function.



.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 42-47
    :lineno-start: 42

A route handler set up with ``put("/{item_title:str}")``, making use of a path parameter,
responds to ``PUT`` requests on the path ``/some todo title``, where ``some todo title``
is the title of the ``TodoItem`` you wish to update. The handler declares
``item_title: FromPath[str]`` to receive the captured value; the :data:`~.params.FromPath`
marker tells Litestar this kwarg comes from the URL path, and the matching name
(``item_title``) lines it up with the ``{item_title:str}`` slot. The ``:str`` suffix in the
path pattern means the value is treated as a string. Additionally, this route handler
receives data of a ``TodoItem`` the same way as the ``POST`` handler.


.. literalinclude:: /examples/todo_app/full_app.py
    :language: python
    :caption: ``app.py``
    :lines: 49
    :lineno-start: 49


An instance of ``Litestar`` is created, including the previously defined route handlers.
This app can now be served using an ASGI server like
`uvicorn <https://uvicorn.env/>`_, which can be conveniently done using Litestar's
CLI by executing the ``litestar run`` command.


Next steps
----------

This tutorial covered some of the fundamental concepts of Litestar. For a more in-depth
explanation of these topics, refer to the :doc:`Usage Guide </usage/index>`.
