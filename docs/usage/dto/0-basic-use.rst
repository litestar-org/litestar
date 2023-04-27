Basic Use
=========

Here we demonstrates how to declare DTO types to your route handlers. For demonstration purposes, we assume that we
are working with a data model ``User``, and already have two DTO types created in our application, ``UserDTO``, and
``UserReturnDTO``.

DTO layer parameters
~~~~~~~~~~~~~~~~~~~~

On every :ref:`Layer <layered-architecture>` of the Litestar application there are two parameters that control the DTOs
that will take responsibility for the data received and returned from handlers:

- ``dto``: This parameter describes the DTO that will be used to parse inbound data to be injected as the ``data``
  keyword argument for a handler. Additionally, if no ``return_dto`` is declared on the handler, this will also be used
  to encode the return data for the handler.
- ``return_dto``: This parameter describes the DTO that will be used to encode data returned from the handler. If not
  provided, the DTO described by the ``dto`` parameter is used.

The object provided to both of these parameters must be a class that conforms to the
:class:`DTOInterface <litestar.dto.interface.DTOInterface>` protocol.

Defining DTOs on handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``dto`` parameter
---------------------

.. literalinclude:: /examples/data_transfer_objects/the_dto_parameter.py
    :caption: Using the ``dto`` Parameter
    :language: python

In this example, ``UserDTO`` performs decoding of client data into the ``User`` type, and encoding of the returned
``User`` instance into a type that Litestar can encode into bytes.

The ``return_dto`` parameter
----------------------------

.. literalinclude:: /examples/data_transfer_objects/the_return_dto_parameter.py
    :caption: Using the ``return_dto`` Parameter
    :language: python

In this example, ``UserDTO`` performs decoding of client data into the ``User`` type, and ``UserReturnDTO`` is
responsible for marshalling the ``User`` instance into a type that Litestar can encode into bytes.

Overriding implicit ``return_dto``
----------------------------------

If a ``return_dto`` type is not declared for a handler, the type declared for the ``dto`` parameter is used for both
decoding and encoding request and response data. If this behavior is undesirable, it can be disabled by explicitly
setting the ``return_dto`` to ``None``.

.. literalinclude:: /examples/data_transfer_objects/overriding_implicit_return_dto.py
    :caption: Disable implicit ``return_dto`` behavior
    :language: python

In this example, we use ``UserDTO`` to decode request data, and marshal it into the ``User`` type, but we want to manage
encoding the response data ourselves, and so we explicitly declare the ``return_dto`` as ``None``.

Defining DTOs on layers
~~~~~~~~~~~~~~~~~~~~~~~

DTOs can be defined on any :ref:`Layer <layered-architecture>` of the application. The DTO type applied is the one
defined in the ownership chain, closest to the handler in question.

.. literalinclude:: /examples/data_transfer_objects/defining_dtos_on_layers.py
    :caption: Controller defined DTOs
    :language: python

In this example, the ``User`` instance received by any handler that declares a ``data`` kwarg, is marshalled by the
``UserDTO`` type, and all handler return values are marshalled into an encodable type by ``UserReturnDTO`` (except for
the ``delete()`` route, which has the ``return_dto`` disabled).

DTOs can similarly be defined on :class:`Routers <litestar.router.Router>` and
:class:`The application <litestar.app.Litestar>` itself.
