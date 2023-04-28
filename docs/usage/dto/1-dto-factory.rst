DTO Factory
===========

Litestar maintains a suite of DTO factory types that can be used to create DTOs for use with popular data modelling
libraries, such as ORMs. These take a model type as a generic type argument, and create subtypes of
:class:`AbstractDTOFactory <litestar.dto.factory.abc.AbstractDTOFactory>` that support conversion of that model type to
and from raw bytes.

The following factories are currently available:

- :class:`DataclassDTO <litestar.dto.factory.stdlib.DataclassDTO>`
- :class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>`

Using DTO Factories
-------------------

DTO factories are used to create DTOs for use with a particular data modelling library. The following example creates
a DTO for use with a SQLAlchemy model:

.. literalinclude:: /examples/data_transfer_objects/factory/simple_dto_factory_example.py
    :caption: A SQLAlchemy model DTO
    :language: python

Here we see that a SQLAlchemy model is used as both the ``data`` and return annotation for the handler, and while
Litestar does not natively support encoding/decoding to/from SQLAlchemy models, through
:class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>` we can do this.

However, we do have some issues with the above example. Firstly, the user's password has been returned to them in the
response from the handler. Secondly, the user is able to set the ``created_at`` field on the model, which should only
ever be set once, and defined internally.

Let's explore how we can configure DTOs to manage scenarios like these.

Marking fields
--------------

The :func:`dto_field <litestar.dto.factory.dto_field>` function can be used to mark model attributes with DTO-based
configuration.

Fields marked as `"private"` or `"read-only"` will not be parsed from client data into the user model, and `"private"`
fields are never serialized into return data.

.. literalinclude:: /examples/data_transfer_objects/factory/marking_fields.py
    :caption: Marking fields
    :language: python
    :emphasize-lines: 6,14,15
    :linenos:

.. note:

    The procedure for "marking" a model field will vary depending on the library. For example,
    :class:`DataclassDTO <.dto.factory.stdlib.dataclass.DataclassDTO>` expects that the mark is made in the ``metadata``
    parameter to ``dataclasses.field``.

Excluding fields
----------------

Fields can be explicitly excluded using :class:`DTOConfig <litestar.dto.factory.DTOConfig>`. The following example
creates an explicit DTO for outbound data which excludes the ``id`` field from the serialized response.

.. literalinclude:: /examples/data_transfer_objects/factory/excluding_fields.py
    :caption: Excluding fields
    :language: python
    :emphasize-lines: 4,7,20,21,23
    :linenos:

Renaming fields
---------------

Fields can be renamed using :class:`DTOConfig <litestar.dto.factory.DTOConfig>`. The following example uses the name
``userName`` client-side, and ``user`` internally.

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_fields.py
    :caption: Renaming fields
    :language: python
    :emphasize-lines: 4,8,19,20,24
    :linenos:

Fields can also be renamed using a renaming strategy that will be applied to all fields. The following example uses a pre-defined rename strategy that will convert all field names to camel case on client-side.

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_all_fields.py
    :caption: Renaming fields
    :language: python
    :emphasize-lines: 4,8,19,20,21,22,24
    :linenos:

Fields that are directly renamed using `rename_fields` mapping will be excluded from `rename_strategy`.

The rename strategy either accepts one of the pre-defined strategies: "camel", "pascal", "upper", "lower" or it can be provided a callback that accepts the field name as an argument and should return a string.

Type checking
-------------

Factories check that the types to which they are assigned are a subclass of the type provided as the generic type to the
DTO factory. This means that if you have a handler that accepts a ``User`` model, and you assign a ``UserDTO`` factory
to it, the DTO will only accept ``User`` types for "data" and return types.

.. literalinclude:: /examples/data_transfer_objects/factory/type_checking.py
    :caption: Type checking
    :language: python
    :emphasize-lines: 25,26,31
    :linenos:

In the above example, the handler is declared to use ``UserDTO`` which has been type-narrowed with the ``User`` type.
However, we annotate the handler with the ``Foo`` type. This will raise an error such as this at runtime:

    litestar.dto.factory.exc.InvalidAnnotation: DTO narrowed with
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.User'>', handler type is
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.Foo'>'

Nested fields
-------------

The depth of related items parsed from client data and serialized into return data can be controlled using the
``max_nested_depth`` parameter to :class:`DTOConfig <litestar.dto.factory.DTOConfig>`.

In this example, we set ``max_nested_depth=0`` for the DTO that handles inbound client data, and leave it at the default
of ``1`` for the return DTO.

.. literalinclude:: /examples/data_transfer_objects/factory/related_items.py
    :caption: Type checking
    :language: python
    :emphasize-lines: 25,35,39
    :linenos:

When the handler receives the client data, we can see that the ``b`` field has not been parsed into the ``A`` model that
is injected for our data parameter (line 35).

We then add a ``B`` instance to the data (line 39), which includes a reference back to ``a``, and from inspection of the
return data can see that ``b`` is included in the response data, however ``b.a`` is not, due to the default
``max_nested_depth`` of ``1``.
