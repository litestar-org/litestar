Data Transfer Object Tutorial
=============================

.. admonition:: Who is this tutorial for?
    :class: info

    This tutorial is intended to familiarize you with the basic concepts of Litestar's
    Data Transfer Objects (DTOs). It is assumed that you are already familiar with
    Litestar and fundamental concepts such as route handlers. If not, it is recommended
    to first follow the
    `Developing a basic TODO application <tutorials/todo-app/3-assembling-the-app.html#final-application>`_
    tutorial.

In this tutorial, we will walk through the process of modelling a simple data structure, and demonstrate how Litestar's
DTO factories can be used to help us build flexible applications.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/initial_pattern.py
    :language: python
    :caption: app.py

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

However, real-world applications are rarely this simple. What if we want to restrict the information about users that we
expose after they have been created? For example, we may want to hide the user's email address from the response. This
is where data transfer objects come in. So, lets now extend our script to include a Data Transfer Object (DTO) that will
ensure we don't expose the user's email in the response.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_dto_example.py
    :language: python
    :caption: app.py
    :emphasize-lines: 6,7,17,18,21
    :linenos:

Here we extend the functionality of our script by introducing a new DTO class (``ReadDTO``) and configuring it to
exclude the ``Person.email`` field. The route handler is also instructed to use the ``ReadDTO`` to handle the response.

Lets look at these changes in more detail. Firstly, we add two additional imports.

The :class:`DTOConfig <litestar.dto.factory.DTOConfig>` class is imported from the ``litestar.dto.factory`` module.
This class is used to configure DTOs. In this case, we are using it to exclude the ``email`` field from the DTO, but
there are many other configuration options available and we'll cover most of them in this tutorial.

The :class:`DataclassDTO <litestar.dto.factory.stdlib.DataclassDTO>` class is imported from the
``litestar.dto.factory.stdlib`` module. This is a factory class that specializes in creating DTOs from dataclasses. It
is also a :class:`Generic <typing.Generic>` class, which means that it it accepts a type parameter. When we provide a
type parameter to a generic class it makes that class a specialized version of the generic class. In this case, we
create a DTO type that specializes in transferring data to and from instances of the ``Person`` class
(``DataclassDTO[Person]``).

.. note::

    It is not necessary to subclass ``DataclassDTO`` to create a specialized DTO type. For instance,
    ``ReadDTO = DataclassDTO[Person]`` also creates a valid, specialized DTO. However, subclassing ``DataclassDTO``
    allows us to add the configuration object, as well as specialize the type.

Finally, we instruct the route handler to use the DTO (``return_dto=ReadDTO``) to transfer data from the handler
response.
