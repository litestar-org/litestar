Implementing Custom DTO Classes
===============================

While Litestar maintains a suite of DTO factories, it is possible to create your own DTOs. To do so, you must implement
the :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` abc.

The following is a description of the methods of the protocol, and how they are used by Litestar. For detailed
information on the signature of each method, see the :class:`reference docs <litestar.dto.base_dto.AbstractDTO>`.

Abstract Methods
~~~~~~~~~~~~~~~~

These methods must be implemented on any :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` subtype.

``generate_field_definitions``
------------------------------

This method receives the model type for the DTO and it should return a generator yielding
:class:`DTOFieldDefinition<litestar.dto.data_structures.DTOFieldDefinition>` instances corresponding with
the model fields.

``detect_nested_field``
-----------------------

This method receives a :class:`FieldDefinition<litestar.typing.FieldDefinition>` instance and it should return a boolean
indicating whether the field is a nested model field.
