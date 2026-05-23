Our first DTO
-------------
In this section we will create our first DTO by extending our script to include a DTO that will ensure we don't expose
the user's email in the response.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_dto_exclude.py
    :language: python
    :caption: ``app.py``
    :emphasize-lines: 6,16,17,20
    :linenos:

Here we introduce a new DTO class (``ReadDTO``) and configure it to exclude the ``Person.email`` field. The route
handler is also instructed to use the DTO to handle the response.

Lets look at these changes in more detail. Firstly, we add two additional imports.

The :class:`DTOConfig <litestar.dto.config.DTOConfig>` class is used to configure DTOs. In this case, we are using it to
exclude the ``email`` field from the DTO, but there are many other configuration options available and we'll cover most
of them in this tutorial.

The :class:`DataclassDTO <litestar.dto.dataclass_dto.DataclassDTO>` class is a factory class that specializes
in creating DTOs from dataclasses. It is also a :class:`Generic <typing.Generic>` class, which means that it accepts
a type parameter. When we provide a type parameter to a generic class it makes that class a specialized version of the
generic class. In this case, we create a DTO type that specializes in transferring data to and from instances of the
``Person`` class (``DataclassDTO[Person]``).

.. note::

    It is not necessary to subclass ``DataclassDTO`` to create a specialized DTO type. For instance,
    ``ReadDTO = DataclassDTO[Person]`` also creates a valid, specialized DTO. However, subclassing ``DataclassDTO``
    allows us to add the configuration object, as well as specialize the type.

Finally, we instruct the route handler to use the DTO (``return_dto=ReadDTO``) to transfer data from the handler
response.

Lets try it out, again visit `<http://localhost:8000/person/peter>`_ and you should see the following response:

.. image:: images/simple_exclude.png
    :align: center

That's better, now we are not exposing the user's email address!
