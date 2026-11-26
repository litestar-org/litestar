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
an attribute typed with its type variable, or a union of generic wrappers holding the model in the same attribute, such
as ``Page[User] | Cursor[User]``. An optional annotation is handled through its only member that is not ``None``; a
union of several types, such as ``User | int | None``, is not handled.

When a DTO cannot handle the annotation, the outcome depends on where it is declared:

- on the route handler: an error when the application is created;
- on a controller, a router or the application, the ``dto`` used for the return value when no ``return_dto`` is
  declared, or created by a serialization plugin: an error if the annotation contains the DTO's model, such as
  ``tuple[User, int]`` or a ``NewType`` of it, skipped otherwise.

The decorator of a controller method declares on the handler, the controller's class attributes on a layer. For a
:class:`~litestar.handlers.WebsocketListener` class, attributes defined in the class body are declared on the handler,
inherited ones on a layer. A skipped ``return_dto`` is not replaced by the ``dto`` or a serialization plugin, and a
skipped ``dto`` is not replaced by a plugin. ``None`` disables DTOs for that direction.

No DTO handles a return annotation of ``None``, ``Any``, a streamed response or server-sent events. With an optional
annotation, ``None`` passes through the DTO in both directions. Form data is decoded into one model, never a
collection.

These errors start with ``[paths='/users', handler='create_user']``:
:exc:`~litestar.exceptions.DTONotApplicableError` when a DTO cannot handle an annotation,
:exc:`~litestar.exceptions.MissingDTOError` when request data is annotated with ``DTOData`` but no DTO decodes it, and
:exc:`~litestar.exceptions.DTOTransferTypeError` when msgspec rejects the transferred type.


Improving performance with the codegen backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    This feature was introduced in ``2.2.0`` and was hidden behind the ``DTO_CODEGEN``
    feature flag. As of ``2.8.0`` it is considered stable and is enabled by default.
    As of ``3.0.0`` it is the only DTO backend.

The DTO backend is the part that does the heavy lifting for all the DTO features. It
is responsible for the transforming, validation and parsing. Because of this,
it is also the part with the most significant performance impact. To reduce the overhead
introduced by the DTOs, the DTO codegen backend was introduced; A DTO backend that
increases efficiency by generating optimized Python code at runtime to perform all the
necessary operations.

Performance improvements
------------------------

These are some preliminary numbers showing the performance increase for certain
operations:

=================================== ===========
operation                           improvement
=================================== ===========
JSON to Python                      ~2.5x
JSON to Python (collection)         ~3.5x
Python to Python                    ~2.5x
Python to Python (collection)       ~5x
Python to JSON                      ~5.3x
Python to JSON (collection)         ~5.4x
=================================== ===========


.. seealso::
    If you are interested in technical details, check out
    https://github.com/litestar-org/litestar/pull/2388
