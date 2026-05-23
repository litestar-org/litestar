Data Transfer Object Tutorial
=============================

.. admonition:: Who is this tutorial for?
    :class: info

    This tutorial is intended to familiarize you with the basic concepts of Litestar's
    Data Transfer Objects (DTOs). It is assumed that you are already familiar with
    Litestar and fundamental concepts such as route handlers. If not, it is recommended
    to first follow the
    `Developing a basic TODO application <../todo-app>`_ tutorial.

In this tutorial, we will walk through the process of modelling a simple data structure, and demonstrate how Litestar's
DTO factories can be used to help us build flexible applications. Lets get started!

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/initial_pattern.py
    :language: python
    :caption: ``app.py``

In this script, we define a data model, a route handler and an application instance.

Our data model is a Python :func:`dataclass <dataclasses.dataclass>` called ``Person`` which has three attributes:
``name``, ``age``, and ``email``.

The function called ``get_person`` that is decorated with :class:`@get() <litestar.handlers.get>` is a route handler
with path ``/person/{name:str}``, that serves `GET <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET>`_
requests. In the path, ``{name:str}`` represents a path parameter called ``name`` with a string type. The route handler
receives the name from the path parameter and returns a ``Person`` object.

Finally, we create an application instance and register the route handler with it.

In Litestar, this pattern works "out-of-the-box" - that is, returning :func:`dataclass <dataclasses.dataclass>`
instances from handlers is natively supported. Litestar will take that dataclass instance, and transform it into
:class:`bytes` that can be sent over the network.

Lets run it and see for ourselves!

Save the above script as ``app.py``, run it using the ``litestar run`` command, and then visit
`<http://localhost:8000/person/peter>`_ in your browser. You should see the
following:

.. image:: images/initial_pattern.png
    :align: center

However, real-world applications are rarely this simple. What if we want to restrict the information about users that we
expose after they have been created? For example, we may want to hide the user's email address from the response. This
is where Data Transfer Objects come in.

.. toctree::
    :hidden:

    01-simple-dto-exclude
    02-nested-exclude
    03-nested-collection-exclude
    04-max-nested-depth
    05-renaming-fields
    06-receiving-data
    07-read-only-fields
    08-dto-data
    09-updating
    10-layered-dto-declarations
