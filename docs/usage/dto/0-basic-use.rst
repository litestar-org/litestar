Basic Use
=========

Here we demonstrate how to declare DTO types to your route handlers. For demonstration purposes, we assume that we
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
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` protocol.

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
responsible for converting the ``User`` instance into a type that Litestar can encode into bytes.

Overriding implicit ``return_dto``
----------------------------------

If a ``return_dto`` type is not declared for a handler, the type declared for the ``dto`` parameter is used for both
decoding and encoding request and response data. If this behavior is undesirable, it can be disabled by explicitly
setting the ``return_dto`` to ``None``.

.. literalinclude:: /examples/data_transfer_objects/overriding_implicit_return_dto.py
    :caption: Disable implicit ``return_dto`` behavior
    :language: python

In this example, we use ``UserDTO`` to decode request data, and convert it into the ``User`` type, but we want to manage
encoding the response data ourselves, and so we explicitly declare the ``return_dto`` as ``None``.

Defining DTOs on layers
~~~~~~~~~~~~~~~~~~~~~~~

DTOs can be defined on any :ref:`Layer <layered-architecture>` of the application. The DTO type applied is the one
defined in the ownership chain, closest to the handler in question.

.. literalinclude:: /examples/data_transfer_objects/defining_dtos_on_layers.py
    :caption: Controller defined DTOs
    :language: python

In this example, the ``User`` instance received by any handler that declares a ``data`` kwarg is converted by the
``UserWriteDTO`` type, and the handler return values are converted into an encodable type by ``UserReadDTO``, except
for ``delete_user()``, which returns ``None``, to which no DTO applies (see `When a DTO applies`_).

DTOs can similarly be defined on :class:`Routers <litestar.router.Router>` and
:class:`The application <litestar.app.Litestar>` itself.

When a DTO applies
~~~~~~~~~~~~~~~~~~

A DTO narrowed with ``User`` handles ``User`` and collections or mappings of ``User`` such as ``list[User]``,
``dict[str, User]`` or ``tuple[User, ...]``, optional or not. For request data it also handles ``DTOData[User]``; for a
return value, one generic wrapper around these, such as ``Response[User]`` or a generic dataclass holding the data in
an attribute typed with its type variable. In an optional union, only the first member that is not ``None`` counts.

When a DTO cannot handle the annotation, the outcome depends on where it is declared:

.. list-table::
    :header-rows: 1

    * - Declared on
      - The DTO handles the annotation
      - The DTO cannot handle it
    * - The route handler
      - Used
      - Error when the application is created
    * - A controller, a router or the application
      - Used
      - Error when the application is created if the annotation contains the DTO's model, such as
        ``tuple[User, int]`` or ``Union[User, Other]``; skipped otherwise
    * - Implicit: the ``dto`` used for the return value when no ``return_dto`` is declared, or a DTO created by a
        serialization plugin
      - Used
      - Skipped

The decorator of a controller method declares on the handler, and the controller's class attributes on a layer. For a
:class:`~litestar.handlers.WebsocketListener` class, attributes defined in the class body are declared on the handler,
and inherited ones on a layer.

The declaration closest to the handler decides: a skipped ``return_dto`` is not replaced by the ``dto`` or a
serialization plugin, and a skipped ``dto`` is not replaced by a plugin. A ``dto`` skipped for the request data, or
declared on a handler without request data, is still used for the return value when no ``return_dto`` is declared
and it handles the return annotation. ``None`` disables DTOs for that direction.

No DTO handles a return annotation of ``None``, ``Any``, a streamed response or server-sent events, nor the
asynchronous generators an HTTP handler returns; the items a websocket stream yields are transferred. With an optional
annotation, ``None`` passes through the DTO in both directions. Form data is decoded into one model, never a
collection, and invalid form data receives the same ``400`` response as invalid JSON data.

DTO errors raised when the application is created start with ``[paths='/users', handler='create_user']``:
:exc:`~litestar.exceptions.DTONotApplicableError` when a DTO cannot handle an annotation as described above,
:exc:`~litestar.exceptions.MissingDTOError` when request data is annotated with ``DTOData`` but no DTO decodes it, and
:exc:`~litestar.exceptions.DTOTransferTypeError` when msgspec rejects the transferred type (see
:ref:`usage/dto/1-abstract-dto:Constraints`).


Code generation
~~~~~~~~~~~~~~~

The DTO backend is the part that does the heavy lifting for all the DTO features. It
is responsible for the transforming, validation and parsing. Because of this,
it is also the part with the most significant performance impact. To reduce the overhead
introduced by the DTOs, the backend generates optimized Python code to perform all the
necessary operations. The code is generated once for every route handler a DTO applies
to, when the handler is registered.

.. seealso::
    If you are interested in technical details, check out
    https://github.com/litestar-org/litestar/pull/2388
